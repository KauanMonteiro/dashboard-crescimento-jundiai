import pandas as pd
import requests

BASE = "https://servicodados.ibge.gov.br/api"
JUNDIAI = 3525904
SETORES = ["Agropecuária", "Indústria", "Serviços", "Administração pública"]


def pegar(url):
    cabecalho = {"User-Agent": "Mozilla/5.0 (projeto-faculdade)"}
    sessao = requests.Session()
    pedido = sessao.prepare_request(requests.Request("GET", url, headers=cabecalho))
    pedido.url = url
    resposta = sessao.send(pedido, timeout=60)
    if resposta.status_code != 200:
        resposta = requests.get(url, headers=cabecalho, timeout=60)
    resposta.raise_for_status()
    return resposta.json()


def buscar_municipio():
    mun = pegar(f"{BASE}/v1/localidades/municipios/{JUNDIAI}")
    micro = mun.get("microrregiao") or {}
    meso = micro.get("mesorregiao") or {}
    uf = meso.get("UF") or {}
    imediata = mun.get("regiao-imediata") or {}
    return {
        "uf": uf.get("sigla", ""),
        "regiao_geografica": (uf.get("regiao") or {}).get("nome", ""),
        "mesorregiao": meso.get("nome", ""),
        "microrregiao": micro.get("nome", ""),
        "regiao_imediata": imediata.get("nome", ""),
        "regiao_intermediaria": (imediata.get("regiao-intermediaria") or {}).get("nome", ""),
    }


def buscar_tabela(tabela, variavel, fonte):
    periodos = "|".join(str(p["id"]) for p in pegar(f"{BASE}/v3/agregados/{tabela}/periodos"))
    url = (f"{BASE}/v3/agregados/{tabela}/periodos/{periodos}/variaveis/{variavel}"
           f"?localidades=N6[{JUNDIAI}]")
    linhas = []
    for var in pegar(url):
        for resultado in var["resultados"]:
            categorias = [list(c["categoria"].values())[0] for c in resultado["classificacoes"]]
            total = all(c.lower() == "total" for c in categorias)
            for serie in resultado["series"]:
                for periodo, valor in serie["serie"].items():
                    linhas.append({"variavel": var["variavel"], "unidade": var.get("unidade", ""),
                                   "ano": int(periodo[:4]), "valor": valor, "total": total, "fonte": fonte})
    return pd.DataFrame(linhas)


def buscar_populacao():
    return pd.concat([buscar_tabela(202, 93, "Censo"),
                      buscar_tabela(4714, 93, "Censo"),
                      buscar_tabela(6579, 9324, "Estimativa")], ignore_index=True)


def buscar_pib():
    return buscar_tabela(5938, "all", "PIB")


def tratar_populacao(bruto, ficha):
    df = bruto[bruto["total"]].copy()
    df["populacao"] = pd.to_numeric(df["valor"], errors="coerce")
    df = df.dropna(subset=["populacao"])
    df["populacao"] = df["populacao"].astype(int)

    df = df.sort_values(["ano", "fonte"]).drop_duplicates("ano")

    anos = df["ano"].diff()
    df["crescimento_abs"] = df["populacao"].diff()
    df["crescimento_pct_ano"] = ((df["populacao"] / df["populacao"].shift()) ** (1 / anos) - 1) * 100

    for campo, valor in ficha.items():
        df[campo] = valor
    return df.drop(columns=["variavel", "unidade", "valor", "total"]).reset_index(drop=True)


def classificar_pib(nome, unidade):
    n = nome.lower()
    if "%" in unidade or "participação" in n or "per capita" in n:
        return None
    if n.startswith("produto interno bruto"):
        return "PIB total"
    if "agropecuária" in n:
        return "Agropecuária"
    if "indústria" in n:
        return "Indústria"
    if "exclusive" in n:
        return "Serviços"
    if "administração" in n:
        return "Administração pública"
    return None


def tratar_pib(bruto):
    df = bruto[bruto["total"]].copy()
    df["categoria"] = [classificar_pib(v, u) for v, u in zip(df["variavel"], df["unidade"])]
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
    df = df.dropna(subset=["categoria", "valor"]).drop_duplicates(["ano", "categoria"])
    return df[["ano", "categoria", "valor"]].sort_values(["categoria", "ano"]).reset_index(drop=True)


def calcular_pib_per_capita(pib, populacao):
    anos = range(populacao["ano"].min(), populacao["ano"].max() + 1)
    pop_por_ano = populacao.set_index("ano")["populacao"].reindex(anos).interpolate()

    per_capita = pib[pib["categoria"] == "PIB total"].copy()
    per_capita["populacao"] = per_capita["ano"].map(pop_por_ano)
    per_capita = per_capita.dropna(subset=["populacao"])
    per_capita["valor"] = per_capita["valor"] * 1000 / per_capita["populacao"]
    per_capita["categoria"] = "PIB per capita"
    return pd.concat([pib, per_capita[pib.columns]], ignore_index=True)


def obter_tudo():
    populacao = tratar_populacao(buscar_populacao(), buscar_municipio())
    pib = calcular_pib_per_capita(tratar_pib(buscar_pib()), populacao)
    return populacao, pib
if __name__ == "__main__":

    print("Buscando dados do IBGE para Jundiaí...")

    populacao, pib = obter_tudo()

    print("Exportando arquivos CSV...")

    populacao.to_csv(
        "populacao_jundiai.csv",
        index=False,
        encoding="utf-8-sig",
        sep=";"
    )

    pib.to_csv(
        "pib_jundiai.csv",
        index=False,
        encoding="utf-8-sig",
        sep=";"
    )

    print("\nArquivos gerados com sucesso!")
