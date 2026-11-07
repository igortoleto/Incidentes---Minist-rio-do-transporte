"""
Coleta dos dados públicos de incidentes de TI do Ministério dos Transportes.

Fonte: Portal de Dados Abertos do Ministério dos Transportes
https://dados.transportes.gov.br/dataset/registro-de-incidentes-e-suporte-de-ti

Usa a API CKAN do portal para listar todos os CSVs mensais, baixa cada um
para a pasta dados/ (cache local) e junta tudo em um único DataFrame.
"""

import io
from pathlib import Path

import pandas as pd
import requests

API = "https://dados.transportes.gov.br/api/3/action/package_show"
DATASET_ID = "6efad694-3ab9-4b66-b5ad-8d7c080b076d"
PASTA_DADOS = Path(__file__).parent / "dados"


def listar_arquivos() -> list[dict]:
    """Retorna os recursos CSV mensais (ignora o dicionário de dados)."""
    pacote = requests.get(API, params={"id": DATASET_ID}, timeout=60).json()["result"]
    return [r for r in pacote["resources"]
            if r["url"].lower().endswith(".csv") and "dicionario" not in r["url"].lower()]


def ler_csv(conteudo: bytes) -> pd.DataFrame:
    """Os arquivos alternam entre UTF-8 e Latin-1; tenta os dois."""
    for codificacao in ("utf-8-sig", "latin-1"):
        try:
            texto = conteudo.decode(codificacao)
            break
        except UnicodeDecodeError:
            continue
    df = pd.read_csv(io.StringIO(texto), sep=";", dtype=str)
    df.columns = df.columns.str.strip()
    return df


def baixar_todos(forcar: bool = False) -> pd.DataFrame:
    PASTA_DADOS.mkdir(exist_ok=True)
    tabelas = []
    for recurso in listar_arquivos():
        nome = recurso["url"].rsplit("/", 1)[-1]
        destino = PASTA_DADOS / nome
        if forcar or not destino.exists():
            try:
                resp = requests.get(recurso["url"], timeout=120)
                resp.raise_for_status()
                destino.write_bytes(resp.content)
                print(f"  baixado: {nome}")
            except requests.RequestException as erro:
                print(f"  falhou:  {nome} ({erro})")
                continue
        df = ler_csv(destino.read_bytes())
        df["arquivo_origem"] = nome
        tabelas.append(df)
    return pd.concat(tabelas, ignore_index=True)


if __name__ == "__main__":
    dados = baixar_todos()
    print(dados.shape)
    presenca = dados.groupby("arquivo_origem").apply(lambda g: g.notna().any())
    print(presenca.sum().sort_values(ascending=False).to_string())
