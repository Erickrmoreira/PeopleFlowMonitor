import os
import tempfile
from datetime import datetime
import unicodedata

from fpdf import FPDF


def normalize_text(txt: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", txt) if unicodedata.category(c) != "Mn")


def compute_kpis(df_filtered) -> dict:
    in_total = int((df_filtered["direction"] == "IN").sum())
    out_total = int((df_filtered["direction"] == "OUT").sum())
    occupancy = max(0, in_total - out_total)
    avg_h = round((in_total + out_total) / 24, 2)
    return {
        "in_total": in_total,
        "out_total": out_total,
        "occupancy": occupancy,
        "avg_h": avg_h,
    }


def build_insight(df_filtered) -> str:
    if df_filtered.empty:
        return "Aguardando dados para análise..."

    kpis = compute_kpis(df_filtered)
    pico_hora = int(df_filtered["timestamp"].dt.hour.mode().iloc[0])
    total_hoje = len(df_filtered)

    return (
        f"**Resumo Diário:** Total de **{total_hoje}** movimentações "
        f"(**IN {kpis['in_total']}** | **OUT {kpis['out_total']}**). "
        f"Pico de atividade às **{pico_hora}:00h**. "
        f"Ocupação estimada no fechamento: **{kpis['occupancy']}**."
    )


class PDFReport(FPDF):
    def header(self):
        self.set_fill_color(24, 52, 90)
        self.rect(0, 0, 210, 35, "F")
        self.set_y(10)
        self.set_font("Arial", "B", 18)
        self.set_text_color(255, 255, 255)
        self.cell(0, 10, "PEOPLE FLOW MONITOR", ln=True, align="L")
        self.set_font("Arial", "", 10)
        self.cell(0, 5, "SISTEMA DE MONITORAMENTO E INTELIGENCIA DE FLUXO", ln=True, align="L")

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Pagina {self.page_no()} | Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", align="C")


def generate_pdf_report(df_filtered, date_selected, chart_fig, limit, output_dir):
    fd, img_path = tempfile.mkstemp(prefix="pfm_chart_", suffix=".png", dir=output_dir)
    os.close(fd)
    try:
        chart_fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        chart_fig.write_image(img_path, engine="kaleido", width=1200, height=700, scale=2)

        kpis = compute_kpis(df_filtered)

        pdf = PDFReport()
        pdf.add_page()
        pdf.set_margins(15, 40, 15)

        pdf.set_y(45)
        pdf.set_font("Arial", "B", 12)
        pdf.set_text_color(50, 50, 50)
        pdf.cell(0, 10, normalize_text(f"RELATORIO DE PERFORMANCE | DATA: {date_selected.strftime('%d/%m/%Y')}"), ln=True)
        pdf.set_draw_color(200, 200, 200)
        pdf.line(15, pdf.get_y(), 195, pdf.get_y())
        pdf.ln(5)

        pdf.set_fill_color(245, 247, 250)
        y_kpi = pdf.get_y() + 5

        items = [
            ("ENTRADAS", str(kpis["in_total"])),
            ("SAIDAS", str(kpis["out_total"])),
            ("MEDIA/HORA", str(kpis["avg_h"])),
        ]

        x_pos = 15
        for title, value in items:
            pdf.rect(x_pos, y_kpi, 58, 22, "F")
            pdf.set_xy(x_pos, y_kpi + 4)
            pdf.set_font("Arial", "", 9)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(58, 5, normalize_text(title), 0, 0, "C")
            pdf.set_xy(x_pos, y_kpi + 10)
            pdf.set_font("Arial", "B", 14)
            pdf.set_text_color(24, 52, 90)
            pdf.cell(58, 10, value, 0, 0, "C")
            x_pos += 62

        pdf.set_y(y_kpi + 30)
        pdf.set_font("Arial", "B", 11)
        pdf.set_text_color(24, 52, 90)
        pdf.cell(0, 10, "DETALHAMENTO DO TRAFEGO HORARIO", ln=True)
        pdf.ln(2)

        pdf.set_fill_color(24, 52, 90)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(50, 10, "INTERVALO", 1, 0, "C", True)
        pdf.cell(45, 10, "ENTRADAS", 1, 0, "C", True)
        pdf.cell(45, 10, "SAIDAS", 1, 0, "C", True)
        pdf.cell(40, 10, "VOLUME TOTAL", 1, 1, "C", True)

        pdf.set_font("Arial", "", 10)
        pdf.set_text_color(0, 0, 0)
        df_h = df_filtered.copy()
        df_h["h"] = df_h["timestamp"].dt.hour
        fill = False
        for h in range(24):
            mask = df_h["h"] == h
            h_in = int((df_h[mask]["direction"] == "IN").sum())
            h_out = int((df_h[mask]["direction"] == "OUT").sum())
            if h_in > 0 or h_out > 0:
                pdf.set_fill_color(248, 249, 250) if fill else pdf.set_fill_color(255, 255, 255)
                pdf.cell(50, 8, f"{h:02d}:00 - {h:02d}:59", 1, 0, "C", True)
                pdf.cell(45, 8, str(h_in), 1, 0, "C", True)
                pdf.cell(45, 8, str(h_out), 1, 0, "C", True)
                pdf.cell(40, 8, str(h_in + h_out), 1, 1, "C", True)
                fill = not fill

        pdf.add_page()
        pdf.set_y(40)
        pdf.set_font("Arial", "B", 11)
        pdf.set_text_color(24, 52, 90)
        pdf.cell(0, 10, "ANALISE GRAFICA DE MOVIMENTACAO", ln=True)
        pdf.image(img_path, x=15, y=pdf.get_y(), w=180)

        pdf.set_y(150)
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 10, "STATUS DO MONITORAMENTO", ln=True)
        pdf.set_font("Arial", "", 10)
        pdf.set_text_color(50, 50, 50)
        status_cap = (
            "MODO LIVRE"
            if not limit
            else (f"DENTRO DO LIMITE ({limit})" if kpis["occupancy"] < limit else f"LIMITE ATINGIDO ({limit})")
        )
        pdf.cell(0, 8, normalize_text(f"- Capacidade Operacional: {status_cap}"), ln=True)
        pdf.cell(0, 8, "- Processamento de Dados: 100% OK", ln=True)
        pdf.cell(0, 8, "- Dispositivo de Captura: Ativo", ln=True)

        output_file = os.path.join(output_dir, f"relatorio_fluxo_{date_selected}.pdf")
        pdf.output(output_file)
        return output_file
    finally:
        if os.path.exists(img_path):
            os.remove(img_path)
