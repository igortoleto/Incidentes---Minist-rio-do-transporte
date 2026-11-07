"""
Projeto de Governança de TI - Análise da Gestão de Incidentes
==============================================================

Base pública: Registro de Incidentes e Suporte de TI do Ministério dos Transportes
(Portal de Dados Abertos - dados.transportes.gov.br), 2021 a 2025.

Referenciais de governança usados:
  - ITIL 4  -> prática de Gerenciamento de Incidentes
  - COBIT 2019 -> objetivo DSS02 (Gerenciar Requisições de Serviço e Incidentes)

Indicadores (KPIs) calculados:
  1. Volume de chamados por tipo (incidente, requisição, mudança, problema)
  2. % de incidentes resolvidos dentro do SLA (geral, por criticidade, por mês)
  3. Tempo de resolução (mediana em horas corridas, estilo MTTR)
  4. Taxa de reabertura (qualidade da solução)
  5. Serviços que mais geram incidentes (Pareto 80/20)
  6. Canal de abertura e horários de pico (dimensionamento da equipe)
"""

import unicodedata
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

import coleta

PASTA_SAIDA = Path(__file__).parent / "saida"
META_SLA = 90.0  # meta de exemplo: 90% dos incidentes resolvidos dentro do prazo


# ----------------------------------------------------------------------------
# 1. Limpeza e padronização
# ----------------------------------------------------------------------------
def sem_acento(texto):
    if pd.isna(texto):
        return texto
    texto = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return " ".join(texto.split()).strip()


def preparar(bruto: pd.DataFrame) -> pd.DataFrame:
    # mantém só arquivos no layout padrão (descarta 2020 e o link quebrado)
    df = bruto[bruto["Numero Chamado"].notna()].copy()

    # categorias com e sem acento -> uma forma só
    for col in ["Disciplina", "Grupo", "Nome", "Descrição", "Serviço", "Estado Chamado",
                "Status Encerramento Chamado", "Meio de Abertura", "Origem da Abertura"]:
        df[col] = df[col].map(sem_acento)
    df["Status Encerramento Chamado"] = df["Status Encerramento Chamado"].replace(
        {"Encerrado Fora Prazo": "Encerrado Fora do Prazo"})

    # datas (alguns meses têm segundos, outros não)
    for col in ["Data/Hora de Criacao", "Data/Hora de Encerramento"]:
        df[col] = pd.to_datetime(df[col], dayfirst=True, format="mixed", errors="coerce")

    # 2022 chamava de "Severidade"; a partir de 2023, "Criticidade"
    sev = df["Severidade"].map({"Severidade 1": "Critico", "Severidade 2": "Critico",
                                "Severidade 3": "Nao Critico"})
    df["criticidade"] = df["Criticidade"].map(sem_acento).fillna(sev).fillna("Nao informado")

    # reabertura tem duas grafias de coluna
    df["reaberto"] = (df["Statu de Reabertura de chamado"]
                      .fillna(df["Status de Reabertura de Chamado"]).eq("REABERTO"))

    # indicadores derivados
    df["tipo"] = df["Disciplina"].replace({"Mudanca Padrao": "Mudanca",
                                           "Mudanca Normal": "Mudanca"})
    # SLA: o status publicado ("Dentro/Fora do Prazo") ficou inconsistente a partir
    # de 04/2025 (mudança de contrato). Por isso recalculamos pela regra
    # tempo em atendimento <= SLA, e só usamos o status publicado quando faltam os números.
    df["sla_status_publicado"] = df["Status Encerramento Chamado"].map(
        {"Encerrado Dentro do Prazo": True, "Encerrado Fora do Prazo": False})  # INDETERMINADO -> NaN
    numero = lambda s: pd.to_numeric(s.str.replace(",", ".").str.strip(), errors="coerce")
    df["tempo_atendimento_min"] = numero(df["Tempo em Atendimento (Min)"])
    df["sla_min"] = numero(df["SLA de Atendimento"])
    calc = df["tempo_atendimento_min"] <= df["sla_min"]
    tem_numeros = df["tempo_atendimento_min"].notna() & df["sla_min"].notna()
    df["sla_status_calculado"] = calc.where(tem_numeros)
    df["dentro_sla"] = df["sla_status_calculado"].fillna(df["sla_status_publicado"])
    df["horas_resolucao"] = (df["Data/Hora de Encerramento"]
                             - df["Data/Hora de Criacao"]).dt.total_seconds() / 3600
    df.loc[df["horas_resolucao"] < 0, "horas_resolucao"] = None
    df["mes"] = df["Data/Hora de Criacao"].dt.to_period("M")
    df["dia_semana"] = df["Data/Hora de Criacao"].dt.day_of_week
    df["hora"] = df["Data/Hora de Criacao"].dt.hour

    # janela de análise: 2022 em diante (2021 só tem resíduos)
    df = df[df["Data/Hora de Criacao"] >= "2022-01-01"]
    return df


# ----------------------------------------------------------------------------
# 2. Indicadores
# ----------------------------------------------------------------------------
def pct(serie: pd.Series) -> float:
    return round(serie.mean() * 100, 1)


def calcular_kpis(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    inc = df[df["tipo"] == "Incidente"]
    r = {}

    r["volume_por_tipo"] = (df["tipo"].value_counts().rename_axis("tipo")
                            .reset_index(name="chamados")
                            .assign(pct=lambda d: (d["chamados"] / d["chamados"].sum() * 100).round(1)))

    r["kpis_gerais"] = pd.DataFrame([
        ("Total de chamados", len(df)),
        ("Total de incidentes", len(inc)),
        ("% incidentes dentro do SLA", pct(inc["dentro_sla"].dropna())),
        ("Meta de SLA (%)", META_SLA),
        ("Tempo mediano de resolução (h)", round(inc["horas_resolucao"].median(), 1)),
        ("Tempo P90 de resolução (h)", round(inc["horas_resolucao"].quantile(0.9), 1)),
        ("% incidentes reabertos", pct(inc["reaberto"])),
        ("% incidentes críticos", pct(inc["criticidade"].eq("Critico"))),
    ], columns=["indicador", "valor"])

    r["sla_por_criticidade"] = (inc.groupby("criticidade")
                                .agg(incidentes=("Numero Chamado", "count"),
                                     pct_dentro_sla=("dentro_sla", lambda s: pct(s.dropna())),
                                     mediana_horas=("horas_resolucao", "median"))
                                .round(1).reset_index())

    r["evolucao_mensal"] = (inc.groupby("mes")
                            .agg(incidentes=("Numero Chamado", "count"),
                                 pct_dentro_sla=("dentro_sla", lambda s: pct(s.dropna())),
                                 mediana_horas=("horas_resolucao", "median"),
                                 reabertos=("reaberto", "sum"))
                            .round(1).reset_index())
    r["evolucao_mensal"]["mes"] = r["evolucao_mensal"]["mes"].astype(str)
    r["evolucao_mensal"]["atingiu_meta"] = r["evolucao_mensal"]["pct_dentro_sla"] >= META_SLA

    # Pareto: quais serviços concentram os incidentes
    pareto = (inc.groupby("Serviço")
              .agg(incidentes=("Numero Chamado", "count"),
                   pct_dentro_sla=("dentro_sla", lambda s: pct(s.dropna())),
                   mediana_horas=("horas_resolucao", "median"))
              .sort_values("incidentes", ascending=False).round(1))
    pareto["pct_acumulado"] = (pareto["incidentes"].cumsum() / pareto["incidentes"].sum() * 100).round(1)
    r["pareto_servicos"] = pareto.reset_index()

    r["por_grupo"] = (inc.groupby("Grupo")
                      .agg(incidentes=("Numero Chamado", "count"),
                           pct_dentro_sla=("dentro_sla", lambda s: pct(s.dropna())),
                           mediana_horas=("horas_resolucao", "median"))
                      .round(1).sort_values("incidentes", ascending=False).reset_index())

    r["canal_abertura"] = (inc["Meio de Abertura"].fillna("Nao informado").value_counts()
                           .rename_axis("canal").reset_index(name="incidentes"))

    dias = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sab", "Dom"]
    r["mapa_calor"] = (inc.pivot_table(index="dia_semana", columns="hora", values="Numero Chamado",
                                       aggfunc="count", fill_value=0)
                       .rename(index=dict(enumerate(dias))))

    # qualidade dos dados: o status publicado concorda com a regra tempo <= SLA?
    ambos = inc[inc["sla_status_publicado"].notna() & inc["sla_status_calculado"].notna()]
    r["qualidade_dados_sla"] = (ambos.assign(
                                    concorda=ambos["sla_status_publicado"] == ambos["sla_status_calculado"].astype(bool))
                                .groupby("mes")
                                .agg(incidentes=("Numero Chamado", "count"),
                                     pct_sla_publicado=("sla_status_publicado", lambda s: pct(s.astype(bool))),
                                     pct_sla_recalculado=("sla_status_calculado", lambda s: pct(s.astype(bool))),
                                     pct_concordancia=("concorda", pct))
                                .reset_index())
    r["qualidade_dados_sla"]["mes"] = r["qualidade_dados_sla"]["mes"].astype(str)

    # incidentes fora do SLA mais demorados -> lista para análise de causa (gestão de problemas)
    r["piores_casos"] = (inc[inc["dentro_sla"] == False]
                         .nlargest(50, "horas_resolucao")
                         [["Numero Chamado", "Data/Hora de Criacao", "Serviço", "criticidade",
                           "Grupo", "horas_resolucao", "Titulo Chamado"]])
    return r


# ----------------------------------------------------------------------------
# 3. Gráficos
# ----------------------------------------------------------------------------
def salvar(fig, nome):
    fig.tight_layout()
    fig.savefig(PASTA_SAIDA / nome, dpi=120)
    plt.close(fig)


def gerar_graficos(r: dict) -> None:
    # 1. Evolução do SLA x meta
    ev = r["evolucao_mensal"]
    fig, ax1 = plt.subplots(figsize=(12, 5))
    ax1.bar(ev["mes"], ev["incidentes"], color="#B0C4DE", label="Incidentes")
    ax1.set_ylabel("Incidentes no mês")
    ax1.tick_params(axis="x", rotation=90)
    ax2 = ax1.twinx()
    ax2.plot(ev["mes"], ev["pct_dentro_sla"], color="#1F4E79", marker="o", label="% dentro do SLA")
    ax2.axhline(META_SLA, color="#C0392B", linestyle="--", label=f"Meta {META_SLA:.0f}%")
    ax2.set_ylabel("% dentro do SLA"); ax2.set_ylim(0, 105)
    ax2.legend(loc="lower left")
    ax1.set_title("Incidentes por mês e cumprimento do SLA")
    salvar(fig, "1_evolucao_sla.png")

    # 2. Pareto dos serviços
    p = r["pareto_servicos"].head(15).iloc[::-1]  # maior no topo
    fig, ax = plt.subplots(figsize=(11, 7))
    ax.barh(p["Serviço"], p["incidentes"], color="#4C72B0")
    for i, (n, acum) in enumerate(zip(p["incidentes"], p["pct_acumulado"])):
        ax.text(n + 40, i, f"{n}  ({acum:.0f}% acum.)", va="center", fontsize=9)
    ax.set_xlim(0, p["incidentes"].max() * 1.3)
    ax.set_xlabel("Incidentes")
    ax.set_title("Pareto: serviços que mais geram incidentes (top 15)")
    salvar(fig, "2_pareto_servicos.png")

    # 3. SLA por criticidade
    c = r["sla_por_criticidade"]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.barh(c["criticidade"], c["pct_dentro_sla"], color="#55A868")
    ax.axvline(META_SLA, color="#C0392B", linestyle="--")
    ax.set_xlim(0, 100); ax.set_xlabel("% dentro do SLA")
    ax.set_title("Cumprimento do SLA por criticidade")
    for i, v in enumerate(c["pct_dentro_sla"]):
        ax.text(v + 1, i, f"{v}%", va="center")
    salvar(fig, "3_sla_criticidade.png")

    # 4. Mapa de calor dia x hora
    m = r["mapa_calor"]
    fig, ax = plt.subplots(figsize=(12, 4))
    im = ax.imshow(m.values, aspect="auto", cmap="Blues")
    ax.set_yticks(range(len(m.index)), m.index)
    ax.set_xticks(range(len(m.columns)), m.columns)
    ax.set_xlabel("Hora de abertura")
    ax.set_title("Quando os incidentes são abertos (dia da semana x hora)")
    fig.colorbar(im, ax=ax, label="Incidentes")
    salvar(fig, "4_mapa_calor.png")


# ----------------------------------------------------------------------------
# 4. Execução
# ----------------------------------------------------------------------------
def main() -> None:
    PASTA_SAIDA.mkdir(exist_ok=True)
    print("Carregando dados (baixa da internet na 1ª execução)...")
    df = preparar(coleta.baixar_todos())
    r = calcular_kpis(df)

    print(f"\nPeríodo: {df['Data/Hora de Criacao'].min():%d/%m/%Y} a "
          f"{df['Data/Hora de Criacao'].max():%d/%m/%Y}")
    print("\n=== KPIs gerais (incidentes) ===");     print(r["kpis_gerais"].to_string(index=False))
    print("\n=== Volume por tipo de chamado ===");   print(r["volume_por_tipo"].to_string(index=False))
    print("\n=== SLA por criticidade ===");          print(r["sla_por_criticidade"].to_string(index=False))
    print("\n=== Top 10 serviços (Pareto) ===")
    print(r["pareto_servicos"].head(10).to_string(index=False))
    ev = r["evolucao_mensal"]
    print(f"\nMeses que atingiram a meta de {META_SLA:.0f}%: "
          f"{ev['atingiu_meta'].sum()} de {len(ev)}")
    q = r["qualidade_dados_sla"]
    ruins = q[q["pct_concordancia"] < 95]
    if len(ruins):
        print(f"\n[ALERTA de qualidade de dados] Status de SLA publicado diverge da regra "
              f"tempo <= SLA em {len(ruins)} meses ({ruins['mes'].iloc[0]} a {ruins['mes'].iloc[-1]}). "
              "SLA recalculado pela regra.")
        print(ruins.to_string(index=False))

    arquivo = PASTA_SAIDA / "relatorio_gestao_incidentes.xlsx"
    with pd.ExcelWriter(arquivo) as w:
        for nome, tabela in r.items():
            tabela.to_excel(w, sheet_name=nome[:31], index=(nome == "mapa_calor"))
    gerar_graficos(r)
    print(f"\nRelatório e gráficos salvos em: {PASTA_SAIDA}")


if __name__ == "__main__":
    main()
