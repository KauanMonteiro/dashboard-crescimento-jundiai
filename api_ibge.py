import pandas as pd
import requests

BASE = "https://servicodados.ibge.gov.br/api"
JUNDIAI = 3525904

HEADERS = {"User-Agent": "Mozilla/5.0 (projeto-faculdade)"}


def _get(url):
    variantes = [
        url,
        url.replace("|", "%7C").replace("[", "%5B").replace("]", "%5D"),
        None
    ]
    erros = []
    for v in variantes:
        try:
            if v is None:
                r = requests.get(url, timeout=60, headers=HEADERS)
            else:
                sessao = requests.Session()
                prep = sessao.prepare_request(requests.Request("GET", v, headers=HEADERS))
                prep.url = v
                r = sessao.send(prep, timeout=60)
            if r.status_code == 200:
                return r.json()
            erros.append(f"HTTP {r.status_code}")
        except requests.RequestException as erro:
            erros.append(str(erro)[:100])
    raise RuntimeError(f"{erros} em {url[:150]}")


def buscar_municipio(cod=JUNDIAI):
    mun = _get(f"{BASE}/v1/localidades/municipios/{cod}")
    micro = mun.get("microrregiao") or {}
    meso = micro.get("mesorregiao") or {}
    uf = meso.get("UF") or {}
    imediata = mun.get("regiao-imediata") or {}
    intermediaria = imediata.get("regiao-intermediaria") or {}
    return {
        "municipio": mun["nome"],
        "uf": uf.get("sigla", ""),
        "regiao_geografica": (uf.get("regiao") or {}).get("nome", ""),
        "mesorregiao": meso.get("nome", ""),
        "microrregiao": micro.get("nome", ""),
        "regiao_imediata": imediata.get("nome", ""),
        "regiao_intermediaria": intermediaria.get("nome", ""),
    }


def _parse(dados, fonte):
    linhas = []
    for var in dados:
        for res in var["resultados"]:
            cats = [list(c["categoria"].values())[0] for c in res["classificacoes"]]
            total = all(c.strip().lower() == "total" for c in cats)
            for s in res["series"]:
                for periodo, valor in s["serie"].items():
                    linhas.append({
                        "cod": int(s["localidade"]["id"]),
                        "nome": s["localidade"]["nome"].split(" - ")[0],
                        "variavel": var["variavel"],
                        "unidade": var.get("unidade", ""),
                        "ano": int(periodo[:4]),
                        "valor": valor,
                        "total": total,
                        "fonte": fonte,
                    })
    return linhas


def _consulta(agregado, variavel, codigos, periodos):
    ids = "|".join(str(c) for c in codigos)
    url = (f"{BASE}/v3/agregados/{agregado}/periodos/{periodos}/variaveis/{variavel}"
           f"?localidades=N6[{ids}]")
    return _get(url)


def _agregado(agregado, variavel, codigos, fonte):
    ids_p = [str(p["id"]) for p in _get(f"{BASE}/v3/agregados/{agregado}/periodos")]
    periodos = ["|".join(ids_p), f"{ids_p[0]}-{ids_p[-1]}"]
    ultimo_erro = None

    for grupos in ([list(codigos)], [[c] for c in codigos]):
        try:
            linhas = []
            for grupo in grupos:
                dados = None
                for per in periodos:
                    try:
                        dados = _consulta(agregado, variavel, grupo, per)
                        break
                    except Exception as erro:
                        ultimo_erro = erro
                if dados is None:
                    raise ultimo_erro
                linhas += _parse(dados, fonte)
            return pd.DataFrame(linhas)
        except Exception as erro:
            ultimo_erro = erro
    raise ultimo_erro


def buscar_populacao(codigos):
    partes, erros = [], []
    for agregado, variavel, fonte in [
        (202, 93, "Censo"),
        (4714, 93, "Censo"),
        (6579, 9324, "Estimativa")
    ]:
        try:
            partes.append(_agregado(agregado, variavel, codigos, fonte))
        except Exception as erro:
            erros.append(f"tabela {agregado}: {erro}")
            print(f"Aviso: tabela {agregado} não carregou ({erro})")

    if not partes:
        raise RuntimeError("Nenhuma tabela de população carregou:\n" + "\n".join(erros))

    return pd.concat(partes, ignore_index=True)


def buscar_pib(codigos):
    return _agregado(5938, "all", codigos, "PIB Municípios")


def tratar_populacao(bruto, info):
    df = bruto[bruto["total"]].copy()
    df["populacao"] = pd.to_numeric(df["valor"], errors="coerce")
    df = df.dropna(subset=["populacao"])
    df["populacao"] = df["populacao"].astype(int)
    df["prioridade"] = (df["fonte"] != "Censo").astype(int)

    df = (
        df.sort_values(["cod", "ano", "prioridade"])
        .drop_duplicates(["cod", "ano"])
        .sort_values(["cod", "ano"])
    )

    g = df.groupby("cod")
    df["crescimento_abs"] = g["populacao"].diff()
    df["anos_intervalo"] = g["ano"].diff()
    df["crescimento_pct_ano"] = (
        (df["populacao"] / g["populacao"].shift()) ** (1 / df["anos_intervalo"]) - 1
    ) * 100

    extras = [k for k in info if k != "municipio"]
    for chave in extras:
        df[chave] = info[chave]

    return df[
        ["cod", "nome", "ano", "populacao", "fonte", "crescimento_abs",
         "anos_intervalo", "crescimento_pct_ano"] + extras
    ].reset_index(drop=True)


def _categoria(nome, unidade):
    n, u = nome.lower(), unidade.lower()

    if "%" in u or "percentual" in n or "participação" in n:
        return None
    if "per capita" in n:
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
    df["categoria"] = [
        _categoria(v, u) for v, u in zip(df["variavel"], df["unidade"])
    ]
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
    df = df.dropna(subset=["categoria", "valor"])
    df = df.drop_duplicates(["cod", "ano", "categoria"])

    return (
        df[["cod", "nome", "ano", "categoria", "valor", "unidade", "variavel"]]
        .sort_values(["nome", "categoria", "ano"])
        .reset_index(drop=True)
    )


def calcular_pib_per_capita(pib, populacao):
    partes = []

    for cod, g in populacao.groupby("cod"):
        serie = g.set_index("ano")["populacao"].sort_index()
        anual = serie.reindex(
            range(int(serie.index.min()), int(serie.index.max()) + 1)
        ).interpolate(method="index")

        base = pib[
            (pib["cod"] == cod) & (pib["categoria"] == "PIB total")
        ].copy()

        base["populacao"] = base["ano"].map(anual)
        partes.append(base.dropna(subset=["populacao"]))

    if not partes:
        return pib

    base = pd.concat(partes)
    base["valor"] = base["valor"] * 1000 / base["populacao"]
    base["categoria"] = "PIB per capita"
    base["unidade"] = "Reais"
    base["variavel"] = "PIB total x 1000 / população do ano (interpolada se faltar)"

    return pd.concat([pib, base[pib.columns]], ignore_index=True)


SETORES = [
    "Agropecuária",
    "Indústria",
    "Serviços",
    "Administração pública"
]


def obter_tudo():
    info = buscar_municipio()
    codigos = [JUNDIAI]
    populacao = tratar_populacao(buscar_populacao(codigos), info)
    pib = calcular_pib_per_capita(tratar_pib(buscar_pib(codigos)), populacao)

    return populacao, pib
