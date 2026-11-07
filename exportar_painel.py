"""Gera os CSVs agregados usados no painel visual (saida/painel/)."""

from pathlib import Path

import pandas as pd

import analise_incidentes as a
import coleta

PASTA = Path(__file__).parent / "saida" / "painel"
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def main() -> None:
    PASTA.mkdir(parents=True, exist_ok=True)
    df = a.preparar(coleta.baixar_todos())
    inc = df[df["tipo"] == "Incidente"]
    r = a.calcular_kpis(df)

    ini, fim = inc["Data/Hora de Criacao"].min(), inc["Data/Hora de Criacao"].max()
    ev = inc.groupby("mes")["dentro_sla"].apply(lambda s: s.dropna().mean())
    pd.DataFrame([{
        "periodo": f"{MESES[ini.month - 1]}/{ini.year} a {MESES[fim.month - 1]}/{fim.year}",
        "chamados": len(df),
        "incidentes": len(inc),
        "pct_sla": round(inc["dentro_sla"].dropna().mean(), 4),
        "meses": int(ev.size),
        "meses_meta": int((ev >= a.META_SLA / 100).sum()),
        "mediana_horas": round(inc["horas_resolucao"].median(), 1),
        "mediana_min_atendimento": round(inc["tempo_atendimento_min"].median(), 0),
        "pct_reaberto": round(inc["reaberto"].mean(), 4),
        "pct_critico": round(inc["criticidade"].eq("Critico").mean(), 4),
    }]).to_csv(PASTA / "kpis.csv", index=False)

    m = inc.groupby("mes").agg(
        incidentes=("Numero Chamado", "count"),
        pct_sla=("dentro_sla", lambda s: s.dropna().mean()),
        pct_sla_publicado=("sla_status_publicado", lambda s: s.dropna().astype(bool).mean()),
    ).round(4).reset_index()
    m["mes"] = m["mes"].astype(str)
    m.to_csv(PASTA / "mensal.csv", index=False)

    s = r["pareto_servicos"].head(10).rename(columns={"Serviço": "servico"})
    acentos = {"perifericos": "periféricos", "Lentidao": "Lentidão", "inicializacao": "inicialização",
               "Usuarios": "Usuários", "impressao": "impressão", "Sistemas Operacional": "Sistema Operacional"}
    for sem, com in acentos.items():
        s["servico"] = s["servico"].str.replace(sem, com, regex=False)
    s["participacao"] =(s["incidentes"] / len(inc)).round(4)
    s["pct_sla"] = (s["pct_dentro_sla"] / 100).round(4)
    s[["servico", "incidentes", "participacao", "pct_sla"]].to_csv(PASTA / "servicos.csv", index=False)

    t = df["tipo"].replace({"Requisicao de Servico": "Requisição de serviço", "Mudanca": "Mudança",
                            "Mudanca Emergencial": "Mudança", "Evento de Sustentacao": "Outros",
                            "Problema": "Problema"})
    t.value_counts().rename_axis("tipo").reset_index(name="chamados").to_csv(PASTA / "tipos.csv", index=False)

    dias = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
    h = inc.groupby(["dia_semana", "hora"]).size().rename("incidentes").reset_index()
    h["dia"] = h["dia_semana"].map(dict(enumerate(dias)))
    h["hora"] = h["hora"].astype(int)
    h[["dia", "hora", "incidentes"]].to_csv(PASTA / "mapa_calor.csv", index=False)

    c = inc.groupby("criticidade").agg(
        incidentes=("Numero Chamado", "count"),
        pct_sla=("dentro_sla", lambda s: s.dropna().mean()),
        mediana_horas=("horas_resolucao", "median")).round({"pct_sla": 4, "mediana_horas": 1}).reset_index()
    c["criticidade"] = c["criticidade"].replace({"Critico": "Crítico", "Nao Critico": "Não crítico",
                                                 "Nao informado": "Não informado"})
    c.to_csv(PASTA / "criticidade.csv", index=False)

    for f in sorted(PASTA.glob("*.csv")):
        print(f"--- {f.name}"); print(f.read_text(encoding="utf-8")[:600])


if __name__ == "__main__":
    main()
