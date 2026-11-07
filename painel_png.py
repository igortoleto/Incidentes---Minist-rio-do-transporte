"""
Painel de Incidentes de TI em imagem (PNG) — feito só com pandas + matplotlib.

Formato retrato 4:5 (2160 x 2700 px), ideal para o feed do LinkedIn.
Usa os CSVs agregados gerados por exportar_painel.py (roda ele se faltarem).

Personalize nas constantes abaixo: cores, autor e logo (opcional).
"""

import textwrap
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import FancyBboxPatch

PASTA = Path(__file__).parent / "saida" / "painel"
SAIDA = Path(__file__).parent / "saida" / "painel_incidentes_ti.png"

# ---- Personalização -------------------------------------------------------
AUTOR = ""            # ex.: "Seu Nome · Governança de TI"
LOGO = None           # ex.: Path("meu_logo.png") — só use logos que você tem direito de usar
META = 0.90           # meta de SLA (referencial de exemplo)

# Paleta inspirada em verde e azul institucionais
AZUL = "#00508C"
AZUL_CLARO = "#DCE8F2"
VERDE = "#00A651"
VERDE_ESCURO = "#007A3D"
TEXTO = "#1F2D35"
SUAVE = "#5F6F78"
FUNDO = "#F4F7F5"
CARD = "#FFFFFF"
BORDA = "#D9E2DD"
BARRA = "#B7C8D6"
ALERTA = "#C0392B"
AVISO_FUNDO = "#FFF6E8"
AVISO_BORDA = "#E09A2B"

plt.rcParams["font.family"] = ["Segoe UI", "DejaVu Sans"]
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


# ---- Formatação pt-BR ------------------------------------------------------
def num(v):
    return f"{int(round(v)):,}".replace(",", ".")


def pct(v, casas=1):
    return f"{v * 100:.{casas}f}%".replace(".", ",")


def dec(v, casas=1):
    return f"{v:.{casas}f}".replace(".", ",")


# ---- Blocos visuais --------------------------------------------------------
def card(fig, x, y, w, h, cor=CARD, borda=BORDA):
    fig.patches.append(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.008",
                                      transform=fig.transFigure, facecolor=cor, edgecolor=borda,
                                      linewidth=1.2, zorder=-10))


def emblema(fig, cx, cy, r):
    """Ícone neutro (sem marca): círculo verde com linha de monitoramento."""
    ax = fig.add_axes([cx - r, cy - r * 1.25, 2 * r, 2 * r * 1.25]); ax.axis("off")
    ax.set_xlim(-1.05, 1.05); ax.set_ylim(-1.05, 1.05); ax.set_aspect("equal")
    ax.add_patch(plt.Circle((0, 0), 1, color=VERDE))
    ax.add_patch(plt.Circle((0, 0), 0.82, fill=False, edgecolor="white", linewidth=1.5, alpha=0.5))
    xs = [-0.62, -0.28, -0.14, 0.02, 0.18, 0.30, 0.62]
    ys = [0.0, 0.0, 0.42, -0.42, 0.22, 0.0, 0.0]
    ax.plot(xs, ys, color="white", linewidth=3.2, solid_capstyle="round", solid_joinstyle="round")


def titulo_card(fig, x, y, titulo, nota=None, largura=60):
    fig.text(x, y, titulo, fontsize=15, fontweight="bold", color=TEXTO, va="top")
    if nota:
        fig.text(x, y - 0.022, textwrap.fill(nota, largura), fontsize=10.5, color=SUAVE, va="top",
                 linespacing=1.4)


def limpar(ax):
    for lado in ["top", "right", "left"]:
        ax.spines[lado].set_visible(False)
    ax.spines["bottom"].set_color(BORDA)
    ax.tick_params(colors=SUAVE, labelsize=10, length=0)
    ax.set_facecolor(CARD)


def main():
    if not (PASTA / "kpis.csv").exists():
        import exportar_painel
        exportar_painel.main()

    k = pd.read_csv(PASTA / "kpis.csv").iloc[0]
    mensal = pd.read_csv(PASTA / "mensal.csv")
    serv = pd.read_csv(PASTA / "servicos.csv")
    heat = pd.read_csv(PASTA / "mapa_calor.csv")

    fig = plt.figure(figsize=(10.8, 13.5), dpi=100, facecolor=FUNDO)

    # ---- Cabeçalho ----
    cab = fig.add_axes([0, 0.885, 1, 0.115]); cab.axis("off")
    cab.add_patch(plt.Rectangle((0, 0), 1, 1, transform=cab.transAxes, color=AZUL))
    fig.add_artist(plt.Rectangle((0, 0.879), 1, 0.006, transform=fig.transFigure, color=VERDE))
    fig.text(0.05, 0.968, " PROJETO PESSOAL ", fontsize=10, color="white", fontweight="bold", va="center",
             bbox=dict(boxstyle="round,pad=0.35,rounding_size=0.8", facecolor=VERDE, edgecolor="none"))
    fig.text(0.205, 0.968, "GOVERNANÇA DE TI  ·  GESTÃO DE INCIDENTES  ·  ITIL 4 & COBIT DSS02",
             fontsize=10.5, color="#BFD6EA", fontweight="bold", va="center")
    fig.text(0.05, 0.928, "Painel de Incidentes de TI", fontsize=32, color="white", fontweight="bold",
             va="center")
    fig.text(0.05, 0.897, f"Chamados de TI do Ministério dos Transportes  ·  {k['periodo']}  ·  dados abertos",
             fontsize=12, color="#DCE8F2", va="center")
    if LOGO and Path(LOGO).exists():
        img = plt.imread(LOGO)
        lax = fig.add_axes([0.80, 0.895, 0.15, 0.08]); lax.imshow(img); lax.axis("off")
    else:
        emblema(fig, 0.905, 0.94, 0.045)

    # ---- Frase principal ----
    conta = serv.loc[serv["servico"] == "Conta bloqueada", "participacao"].iloc[0]
    fig.text(0.05, 0.852,
             f"{pct(k['pct_sla'])} dos {num(k['incidentes'])} incidentes foram resolvidos dentro do SLA.",
             fontsize=17, color=TEXTO, fontweight="bold", va="top")
    fig.text(0.05, 0.826,
             f"Um único problema, conta bloqueada, respondeu por {pct(conta)} deles.",
             fontsize=14, color=SUAVE, va="top")

    # ---- KPIs ----
    kpis = [
        ("RESOLVIDOS NO SLA", pct(k["pct_sla"]), VERDE_ESCURO,
         f"{int(k['meses_meta'])} de {int(k['meses'])} meses acima da meta de {pct(META, 0)}"),
        ("INCIDENTES", num(k["incidentes"]), AZUL,
         f"de {num(k['chamados'])} chamados; {pct(k['pct_critico'], 0)} críticos"),
        ("TEMPO DE ATENDIMENTO", f"{num(k['mediana_min_atendimento'])} min", AZUL,
         f"mediana no relógio do SLA; {dec(k['mediana_horas'])} h corridas"),
        ("REABERTURA", pct(k["pct_reaberto"]), AZUL,
         "incidentes que voltaram após o encerramento"),
    ]
    w, gap, x0, y0, h = 0.2125, 0.0167, 0.05, 0.665, 0.125
    for i, (rot, val, cor, sub) in enumerate(kpis):
        x = x0 + i * (w + gap)
        card(fig, x, y0, w, h)
        fig.text(x + 0.018, y0 + h - 0.02, rot, fontsize=9, color=SUAVE, fontweight="bold", va="top")
        fig.text(x + 0.018, y0 + h - 0.045, val, fontsize=27, color=cor, fontweight="bold", va="top")
        fig.text(x + 0.018, y0 + 0.035, textwrap.fill(sub, 30), fontsize=9, color=SUAVE, va="top",
                 linespacing=1.35)

    # ---- Evolução mensal ----
    card(fig, 0.05, 0.355, 0.90, 0.29)
    titulo_card(fig, 0.075, 0.630, "Cumprimento do SLA e volume de incidentes por mês")
    mensal["data"] = pd.to_datetime(mensal["mes"] + "-01")
    xs = np.arange(len(mensal))

    ax = fig.add_axes([0.11, 0.475, 0.78, 0.12]); limpar(ax)
    ax.axhline(META, color=SUAVE, linestyle=(0, (4, 3)), linewidth=1.2)
    ax.text(0.5, META - 0.13, f"meta {pct(META, 0)}", color=SUAVE, fontsize=9.5)
    ax.plot(xs, mensal["pct_sla_publicado"], color=ALERTA, linestyle=(0, (4, 3)), linewidth=2,
            label="Status publicado no portal")
    ax.plot(xs, mensal["pct_sla"], color=VERDE, linewidth=3, solid_capstyle="round",
            label="SLA recalculado (tempo ≤ prazo)")
    u = mensal.iloc[-1]
    for col, cor in [("pct_sla", VERDE_ESCURO), ("pct_sla_publicado", ALERTA)]:
        ax.scatter(xs[-1], u[col], color=cor, s=30, zorder=3)
        ax.text(xs[-1] + 0.8, u[col], pct(u[col]), color=cor, fontsize=10.5, fontweight="bold", va="center")
    ax.set_ylim(-0.03, 1.08); ax.set_xlim(-0.8, len(xs) - 0.2)
    ax.set_yticks([0, 0.5, 1]); ax.set_yticklabels(["0%", "50%", "100%"])
    ax.set_xticks([]); ax.spines["bottom"].set_visible(False)
    ax.grid(axis="y", color=BORDA, linewidth=0.8); ax.set_axisbelow(True)
    ax.legend(loc="lower left", frameon=False, fontsize=9.5, ncol=2, bbox_to_anchor=(0, -0.02),
              labelcolor=TEXTO)

    ax2 = fig.add_axes([0.11, 0.39, 0.78, 0.07]); limpar(ax2)
    ax2.bar(xs, mensal["incidentes"], color=BARRA, width=0.72)
    ax2.set_xlim(-0.8, len(xs) - 0.2)
    ax2.set_yticks([0, 400]); ax2.set_yticklabels(["0", "400"])
    jan = mensal.index[mensal["data"].dt.month == 1]
    ax2.set_xticks(jan); ax2.set_xticklabels(mensal.loc[jan, "data"].dt.year)
    ax2.text(-0.8, 760, "incidentes no mês", color=SUAVE, fontsize=9.5)

    # ---- Alerta de qualidade de dados ----
    card(fig, 0.05, 0.268, 0.90, 0.072, cor=AVISO_FUNDO, borda=AVISO_BORDA)
    fig.text(0.075, 0.327, "ACHADO DE QUALIDADE DE DADOS", fontsize=9.5, color="#A8650F",
             fontweight="bold", va="top")
    fig.text(0.075, 0.307, textwrap.fill(
        f"Desde abr/2025 o status “dentro do prazo” publicado no portal não bate com o tempo real de "
        f"atendimento. Pelo status, o SLA de out/2025 seria {pct(u['pct_sla_publicado'])}; recalculado, "
        f"é {pct(u['pct_sla'])}. Indicador sem validação é risco de governança (COBIT MEA01).", 118),
        fontsize=10.5, color=TEXTO, va="top", linespacing=1.4)

    # ---- Pareto dos serviços ----
    card(fig, 0.05, 0.055, 0.44, 0.198)
    titulo_card(fig, 0.07, 0.240, "Onde nascem os incidentes")
    top = serv.head(6)
    axp = fig.add_axes([0.07, 0.07, 0.40, 0.14]); axp.axis("off")
    axp.set_xlim(0, top["incidentes"].max() * 1.45); axp.set_ylim(len(top) - 0.3, -0.9)
    for i, r in top.reset_index(drop=True).iterrows():
        cor = VERDE if i == 0 else BARRA
        axp.text(0, i - 0.38, textwrap.shorten(r["servico"], 46, placeholder="…"), fontsize=9.5,
                 color=TEXTO, va="center")
        axp.barh(i + 0.05, r["incidentes"], height=0.32, color=cor)
        axp.text(r["incidentes"] + top["incidentes"].max() * 0.02, i + 0.05,
                 f"{num(r['incidentes'])} · {pct(r['participacao'])}", fontsize=9, color=SUAVE, va="center")

    # ---- Mapa de calor ----
    card(fig, 0.51, 0.055, 0.44, 0.198)
    titulo_card(fig, 0.53, 0.240, "Quando os incidentes chegam")
    dias = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
    horas = list(range(6, 22))
    mat = (heat.pivot_table(index="dia", columns="hora", values="incidentes", fill_value=0)
           .reindex(index=dias, columns=horas, fill_value=0))
    cmap = LinearSegmentedColormap.from_list("verde", ["#F1F7F3", "#7FD0A2", VERDE, VERDE_ESCURO])
    axh = fig.add_axes([0.56, 0.08, 0.37, 0.125])
    axh.imshow(np.sqrt(mat.values), aspect="auto", cmap=cmap)
    axh.set_yticks(range(7)); axh.set_yticklabels(dias)
    axh.set_xticks(range(0, 16, 3)); axh.set_xticklabels([f"{h}h" for h in horas[::3]])
    axh.tick_params(colors=SUAVE, labelsize=9.5, length=0)
    for s in axh.spines.values():
        s.set_visible(False)
    axh.set_xticks(np.arange(-0.5, 16, 1), minor=True); axh.set_yticks(np.arange(-0.5, 7, 1), minor=True)
    axh.grid(which="minor", color=CARD, linewidth=2); axh.tick_params(which="minor", length=0)
    fig.text(0.53, 0.218, "Pico das 9h às 11h; vale no almoço", fontsize=10.5, color=SUAVE, va="top")

    # ---- Rodapé ----
    fonte = ("Fonte: Registro de Incidentes e Suporte de TI — Portal de Dados Abertos do Ministério dos "
             "Transportes (dados.transportes.gov.br). Análise em Python · pandas · matplotlib. "
             f"Meta de {pct(META, 0)} é referencial de exemplo. "
             "Projeto pessoal de estudo, sem vínculo com o Ministério dos Transportes.")
    fig.text(0.05, 0.035, textwrap.fill(fonte, 150), fontsize=8.5, color=SUAVE, va="top", linespacing=1.4)
    if AUTOR:
        fig.text(0.95, 0.035, AUTOR, fontsize=9.5, color=AZUL, fontweight="bold", va="top", ha="right")

    fig.savefig(SAIDA, dpi=200, facecolor=FUNDO)
    print(f"Painel salvo em: {SAIDA}")


if __name__ == "__main__":
    main()
