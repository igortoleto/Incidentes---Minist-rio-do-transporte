"""
Painel de Incidentes de TI interativo — feito só com pandas + Plotly.

Gera um único arquivo HTML (saida/painel_interativo.html) que abre em qualquer
navegador, funciona offline e permite passar o mouse, dar zoom e ligar/desligar séries.
Usa os CSVs agregados de exportar_painel.py (roda ele se faltarem).
"""

import webbrowser
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

PASTA = Path(__file__).parent / "saida" / "painel"
SAIDA = Path(__file__).parent / "saida" / "painel_interativo.html"

AUTOR = ""      # ex.: "Seu Nome · Governança de TI"
META = 0.90

AZUL, AZUL_CLARO = "#00508C", "#DCE8F2"
VERDE, VERDE_ESCURO = "#00A651", "#007A3D"
TEXTO, SUAVE, FUNDO, CARD, BORDA = "#1F2D35", "#5F6F78", "#F4F7F5", "#FFFFFF", "#D9E2DD"
BARRA, ALERTA = "#B7C8D6", "#C0392B"
FONTE = "Segoe UI, Roboto, Helvetica, Arial, sans-serif"
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def num(v):
    return f"{int(round(v)):,}".replace(",", ".")


def pct(v, casas=1):
    return f"{v * 100:.{casas}f}%".replace(".", ",")


def dec(v, casas=1):
    return f"{v:.{casas}f}".replace(".", ",")


def estilo(fig, altura):
    fig.update_layout(
        height=altura, margin=dict(l=10, r=20, t=10, b=10),
        paper_bgcolor=CARD, plot_bgcolor=CARD,
        font=dict(family=FONTE, color=TEXTO, size=13),
        hoverlabel=dict(bgcolor="white", bordercolor=BORDA, font=dict(family=FONTE, color=TEXTO)),
        separators=",.",
    )
    fig.update_xaxes(showgrid=False, linecolor=BORDA, tickfont=dict(color=SUAVE))
    fig.update_yaxes(gridcolor="#E8EEEA", zeroline=False, tickfont=dict(color=SUAVE))
    return fig


# ---- Gráficos ---------------------------------------------------------------
def grafico_mensal(m):
    m = m.copy()
    m["data"] = pd.to_datetime(m["mes"] + "-01")
    m["rotulo"] = [f"{MESES[d.month - 1]}/{d.year}" for d in m["data"]]
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.06)
    fig.add_trace(go.Scatter(
        x=m["data"], y=m["pct_sla"], name="SLA recalculado (tempo ≤ prazo)", mode="lines+markers",
        line=dict(color=VERDE, width=3), marker=dict(size=5), customdata=m["rotulo"],
        hovertemplate="%{customdata}<br>SLA recalculado: %{y:.1%}<extra></extra>"), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=m["data"], y=m["pct_sla_publicado"], name="Status publicado no portal", mode="lines",
        line=dict(color=ALERTA, width=2, dash="dash"), customdata=m["rotulo"],
        hovertemplate="%{customdata}<br>Status publicado: %{y:.1%}<extra></extra>"), row=1, col=1)
    fig.add_hline(y=META, line=dict(color=SUAVE, dash="dot", width=1.5), row=1, col=1,
                  annotation_text=f"meta {pct(META, 0)}", annotation_position="bottom left",
                  annotation_font=dict(color=SUAVE, size=12))
    fig.add_trace(go.Bar(
        x=m["data"], y=m["incidentes"], name="Incidentes no mês", marker_color=BARRA,
        customdata=m["rotulo"], hovertemplate="%{customdata}<br>%{y:,} incidentes<extra></extra>"),
        row=2, col=1)
    fig.update_yaxes(tickformat=".0%", range=[-0.03, 1.06], row=1, col=1)
    fig.update_yaxes(title_text="incidentes", title_font=dict(color=SUAVE, size=12), row=2, col=1)
    estilo(fig, 470)
    fig.update_layout(legend=dict(orientation="h", y=1.08, x=0, font=dict(size=12)), hovermode="x unified",
                      bargap=0.25)
    marcas = m[m["data"].dt.month.isin([1, 7])]
    fig.update_xaxes(tickvals=marcas["data"], ticktext=marcas["rotulo"], row=2, col=1)
    fig.update_xaxes(rangeslider=dict(visible=False), row=2, col=1)
    return fig


def grafico_servicos(s):
    s = s.iloc[::-1]
    cores = [BARRA] * (len(s) - 1) + [VERDE]
    fig = go.Figure(go.Bar(
        x=s["incidentes"], y=s["servico"], orientation="h", marker_color=cores,
        text=[f"{num(n)} · {pct(p)}" for n, p in zip(s["incidentes"], s["participacao"])],
        textposition="outside", textfont=dict(color=SUAVE, size=12), cliponaxis=False,
        customdata=s["pct_sla"],
        hovertemplate="<b>%{y}</b><br>%{x:,} incidentes<br>No SLA: %{customdata:.1%}<extra></extra>"))
    estilo(fig, 430)
    fig.update_xaxes(showticklabels=False, range=[0, s["incidentes"].max() * 1.45])
    fig.update_yaxes(gridcolor=CARD, tickfont=dict(color=TEXTO, size=12))
    return fig


def grafico_calor(h):
    dias = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
    horas = list(range(6, 22))
    mat = (h.pivot_table(index="dia", columns="hora", values="incidentes", fill_value=0)
           .reindex(index=dias, columns=horas, fill_value=0))
    fig = go.Figure(go.Heatmap(
        z=mat.values, x=[f"{x}h" for x in horas], y=dias, xgap=3, ygap=3,
        colorscale=[[0, "#F1F7F3"], [0.35, "#7FD0A2"], [0.7, VERDE], [1, VERDE_ESCURO]],
        colorbar=dict(title=dict(text="incidentes", font=dict(size=11, color=SUAVE)), thickness=10,
                      tickfont=dict(color=SUAVE)),
        hovertemplate="%{y}, %{x}<br>%{z:,} incidentes<extra></extra>"))
    estilo(fig, 330)
    fig.update_yaxes(autorange="reversed", gridcolor=CARD)
    return fig


def grafico_tipos(t):
    cores = [VERDE if x == "Incidente" else c for x, c in
             zip(t["tipo"], [AZUL, "#4F86B5", "#8FB3D3", "#C3D6E6", "#E1EAF2"])]
    fig = go.Figure(go.Pie(
        labels=t["tipo"], values=t["chamados"], hole=0.62, marker=dict(colors=cores, line=dict(color=CARD, width=2)),
        sort=False, textinfo="percent", textfont=dict(color="white"),
        hovertemplate="<b>%{label}</b><br>%{value:,} chamados<br>%{percent}<extra></extra>"))
    estilo(fig, 330)
    fig.update_layout(legend=dict(font=dict(size=12)),
                      annotations=[dict(text=f"<b>{num(t['chamados'].sum())}</b><br>chamados", showarrow=False,
                                        font=dict(size=15, color=TEXTO))])
    return fig


def grafico_criticidade(c):
    fig = go.Figure(go.Bar(
        x=c["criticidade"], y=c["pct_sla"], marker_color=[AZUL, "#4F86B5", "#8FB3D3"],
        text=[pct(v) for v in c["pct_sla"]], textposition="outside", cliponaxis=False,
        customdata=list(zip(c["incidentes"], c["mediana_horas"])),
        hovertemplate=("<b>%{x}</b><br>No SLA: %{y:.1%}<br>%{customdata[0]:,} incidentes"
                       "<br>Mediana: %{customdata[1]:.1f} h corridas<extra></extra>"),
        width=0.5))
    fig.add_hline(y=META, line=dict(color=SUAVE, dash="dot", width=1.5),
                  annotation_text=f"meta {pct(META, 0)}", annotation_font=dict(color=SUAVE, size=12))
    estilo(fig, 330)
    fig.update_yaxes(tickformat=".0%", range=[0, 1.12])
    return fig


# ---- Página -------------------------------------------------------------------
EMBLEMA = f"""<svg width="64" height="64" viewBox="-1.05 -1.05 2.1 2.1" aria-hidden="true">
<circle r="1" fill="{VERDE}"/><circle r="0.82" fill="none" stroke="white" stroke-opacity=".5" stroke-width=".04"/>
<polyline points="-0.62,0 -0.28,0 -0.14,-0.42 0.02,0.42 0.18,-0.22 0.30,0 0.62,0" fill="none"
 stroke="white" stroke-width=".11" stroke-linecap="round" stroke-linejoin="round"/></svg>"""

CSS = f"""
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: {FUNDO}; color: {TEXTO}; font-family: {FONTE}; }}
.cab {{ background: {AZUL}; border-bottom: 6px solid {VERDE}; }}
.cab-in, .corpo {{ max-width: 1200px; margin: 0 auto; padding: 0 24px; }}
.cab-in {{ display: flex; justify-content: space-between; align-items: center; gap: 24px; padding-block: 28px; }}
.olho {{ color: #BFD6EA; font-size: 12px; font-weight: 700; letter-spacing: .08em; margin: 0 0 8px; }}
h1 {{ color: #fff; font-size: clamp(28px, 4vw, 42px); margin: 0 0 6px; }}
.sub {{ color: {AZUL_CLARO}; margin: 0; font-size: 15px; }}
.sub b {{ color: #fff; }}
.aviso {{ color: #BFD6EA; margin: 6px 0 0; font-size: 12.5px; font-style: italic; }}
.selo {{ background: {VERDE}; color: #fff; border-radius: 999px; padding: 3px 10px; margin-right: 8px; letter-spacing: .06em; }}
.corpo {{ display: grid; gap: 20px; padding-block: 28px 40px; }}
.frase {{ margin: 0; font-size: 22px; font-weight: 700; }}
.frase2 {{ margin: 4px 0 0; font-size: 17px; color: {SUAVE}; }}
.kpis {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; }}
.card {{ background: {CARD}; border: 1px solid {BORDA}; border-radius: 10px; padding: 20px; min-width: 0; }}
.rot {{ font-size: 12px; font-weight: 700; color: {SUAVE}; letter-spacing: .06em; margin: 0; }}
.val {{ font-size: 36px; font-weight: 700; color: {AZUL}; margin: 6px 0; }}
.val.ok {{ color: {VERDE_ESCURO}; }}
.desc {{ font-size: 13px; color: {SUAVE}; margin: 0; line-height: 1.4; }}
h2 {{ font-size: 18px; margin: 0 0 4px; }}
.nota {{ font-size: 13px; color: {SUAVE}; margin: 0 0 8px; line-height: 1.45; }}
.grade {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 480px), 1fr)); gap: 20px; }}
.alerta {{ background: #FFF6E8; border: 1px solid #E09A2B; border-radius: 10px; padding: 18px 20px; }}
.alerta .rot {{ color: #A8650F; }}
.alerta p {{ margin: 6px 0 0; line-height: 1.5; }}
.ruim {{ color: {ALERTA}; font-weight: 700; }}
.bom {{ color: {VERDE_ESCURO}; font-weight: 700; }}
.grade > *, .card > div {{ min-width: 0; }}
.plotly-graph-div {{ width: 100% !important; }}
footer {{ font-size: 12px; color: {SUAVE}; border-top: 1px solid {BORDA}; padding-top: 14px; line-height: 1.5; }}
footer a {{ color: inherit; }}
"""


def main():
    if not (PASTA / "kpis.csv").exists():
        import exportar_painel
        exportar_painel.main()

    k = pd.read_csv(PASTA / "kpis.csv").iloc[0]
    mensal = pd.read_csv(PASTA / "mensal.csv")
    serv = pd.read_csv(PASTA / "servicos.csv")
    heat = pd.read_csv(PASTA / "mapa_calor.csv")
    tipos = pd.read_csv(PASTA / "tipos.csv")
    crit = pd.read_csv(PASTA / "criticidade.csv")

    conta = serv.loc[serv["servico"] == "Conta bloqueada", "participacao"].iloc[0]
    ult = mensal.iloc[-1]
    cfg = {"displaylogo": False, "locale": "pt-BR", "responsive": True,
           "modeBarButtonsToRemove": ["lasso2d", "select2d"]}

    graficos = {}
    primeiro = True
    for nome, fig in [("mensal", grafico_mensal(mensal)), ("servicos", grafico_servicos(serv)),
                      ("calor", grafico_calor(heat)), ("tipos", grafico_tipos(tipos)),
                      ("crit", grafico_criticidade(crit))]:
        graficos[nome] = fig.to_html(full_html=False, include_plotlyjs=primeiro, config=cfg,
                                     default_width="100%")
        primeiro = False  # a biblioteca vai embutida só uma vez (arquivo funciona offline)

    kpis = [
        ("RESOLVIDOS NO SLA", pct(k["pct_sla"]), "ok",
         f"{int(k['meses_meta'])} de {int(k['meses'])} meses acima da meta de {pct(META, 0)}"),
        ("INCIDENTES", num(k["incidentes"]), "", f"de {num(k['chamados'])} chamados; {pct(k['pct_critico'], 0)} críticos"),
        ("TEMPO DE ATENDIMENTO", f"{num(k['mediana_min_atendimento'])} min", "",
         f"mediana no relógio do SLA; {dec(k['mediana_horas'])} h corridas"),
        ("REABERTURA", pct(k["pct_reaberto"]), "", "incidentes que voltaram após o encerramento"),
    ]
    cards = "".join(f'<div class="card"><p class="rot">{r}</p><p class="val {c}">{v}</p><p class="desc">{d}</p></div>'
                    for r, v, c, d in kpis)
    autor = f" · {AUTOR}" if AUTOR else ""

    html = f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Painel de Incidentes de TI</title><style>{CSS}</style></head>
<body>
<header class="cab"><div class="cab-in">
  <div>
    <p class="olho"><span class="selo">PROJETO PESSOAL</span> GOVERNANÇA DE TI · GESTÃO DE INCIDENTES · ITIL 4 &amp; COBIT DSS02</p>
    <h1>Painel de Incidentes de TI</h1>
    <p class="sub">Análise dos chamados de TI do <b>Ministério dos Transportes</b> · {k['periodo']} · dados abertos</p>
    <p class="aviso">Projeto pessoal de estudo, sem vínculo com o Ministério dos Transportes.</p>
  </div>
  {EMBLEMA}
</div></header>
<main class="corpo">
  <div>
    <p class="frase">{pct(k['pct_sla'])} dos {num(k['incidentes'])} incidentes foram resolvidos dentro do SLA.</p>
    <p class="frase2">Um único problema, conta bloqueada, respondeu por {pct(conta)} deles.</p>
  </div>
  <section class="kpis">{cards}</section>
  <section class="card">
    <h2>Cumprimento do SLA e volume de incidentes por mês</h2>
    <p class="nota">Passe o mouse para ver cada mês. Clique na legenda para ligar ou desligar uma série e arraste para dar zoom (duplo clique volta).</p>
    {graficos['mensal']}
  </section>
  <section class="alerta">
    <p class="rot">ACHADO DE QUALIDADE DE DADOS</p>
    <p>Desde abr/2025 o status “dentro do prazo” publicado no portal não bate com o tempo real de atendimento.
    Pelo status, o SLA de out/2025 seria <span class="ruim">{pct(ult['pct_sla_publicado'])}</span>; recalculado pela regra
    do contrato, é <span class="bom">{pct(ult['pct_sla'])}</span>. Indicador publicado sem validação é risco de governança (COBIT MEA01).</p>
  </section>
  <div class="grade">
    <section class="card">
      <h2>Onde nascem os incidentes</h2>
      <p class="nota">Os 10 serviços com mais incidentes e sua participação no total.</p>
      {graficos['servicos']}
    </section>
    <section class="card">
      <h2>Quando os incidentes chegam</h2>
      <p class="nota">Incidentes por dia da semana e hora de abertura, das 6h às 21h. Pico das 9h às 11h.</p>
      {graficos['calor']}
    </section>
  </div>
  <div class="grade">
    <section class="card">
      <h2>Tipos de chamado</h2>
      <p class="nota">Incidentes são falhas a restaurar; requisições e mudanças são pedidos planejados.</p>
      {graficos['tipos']}
    </section>
    <section class="card">
      <h2>SLA por criticidade</h2>
      <p class="nota">Passe o mouse para ver o volume e o tempo mediano de cada nível.</p>
      {graficos['crit']}
    </section>
  </div>
  <footer>
    Fonte: Registro de Incidentes e Suporte de TI — Portal de Dados Abertos do Ministério dos Transportes
    (<a href="https://dados.transportes.gov.br/dataset/registro-de-incidentes-e-suporte-de-ti">dados.transportes.gov.br</a>).
    Análise em Python · pandas · Plotly. Meta de {pct(META, 0)} é referencial de exemplo.
    Projeto pessoal, sem vínculo com o órgão.{autor}
  </footer>
</main>
<script>
  // reajusta cada gráfico ao tamanho real do seu cartão depois que a página monta
  const ajustar = () => document.querySelectorAll('.plotly-graph-div').forEach((d) => Plotly.Plots.resize(d));
  window.addEventListener('load', () => {{ ajustar(); setTimeout(ajustar, 300); }});
</script>
</body></html>"""

    SAIDA.write_text(html, encoding="utf-8")
    # cópia em docs/ para publicar com o GitHub Pages
    docs = Path(__file__).parent / "docs"
    docs.mkdir(exist_ok=True)
    (docs / "index.html").write_text(html, encoding="utf-8")
    print(f"Painel interativo salvo em: {SAIDA} (e docs/index.html)")
    webbrowser.open(SAIDA.resolve().as_uri())


if __name__ == "__main__":
    main()
