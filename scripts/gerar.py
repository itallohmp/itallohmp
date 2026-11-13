#!/usr/bin/env python3
"""Gera as imagens do README do perfil, cada uma em versão clara e escura.

    GH_TOKEN=<token> python scripts/gerar.py

Com GH_TOKEN, busca os números do último ano na API do GitHub e refaz o quadro de
estatísticas. Sem ele, refaz só as imagens fixas (projetos e stack) e deixa as
estatísticas como estão. Só usa a biblioteca padrão: a tarefa diária não instala nada.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import time
import urllib.error
import urllib.request
from html import escape
from pathlib import Path

USUARIO = "itallohmp"
RAIZ = Path(__file__).resolve().parent.parent
ASSETS = RAIZ / "assets"
ICONES = json.loads((Path(__file__).parent / "icones.json").read_text(encoding="utf-8"))

SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace"

TEMAS = {
    "claro": {
        "fundo": "#ffffff", "borda": "#d0d7de", "tinta": "#1f2328", "fraco": "#59636e",
        "pilula": "#f6f8fa", "tracejado": "#d8dee4", "verde": "#1a7f37", "azul": "#0969da",
        "niveis": ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"],
    },
    "escuro": {
        "fundo": "#0d1117", "borda": "#30363d", "tinta": "#e6edf3", "fraco": "#8d96a0",
        "pilula": "#161b22", "tracejado": "#21262d", "verde": "#3fb950", "azul": "#4493f8",
        "niveis": ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"],
    },
}

# ---------------------------------------------------------------- conteúdo

PROJETOS = [
    {
        "arquivo": "projeto-invicta", "numero": "01", "titulo": "Sistema da Invicta",
        "status": "em produção", "cor": "verde",
        "descricao": ["licitações sob medida: orçamentos, catálogo com foto e",
                      "cobrança por whatsapp. uma instância por cliente."],
        "tags": ["fastapi", "react", "postgresql", "docker", "argon2id"],
    },
    {
        "arquivo": "projeto-painel", "numero": "02", "titulo": "Painel das instâncias",
        "status": "em produção", "cor": "verde",
        "descricao": ["cria, atualiza e controla a instância de cada cliente,",
                      "com deploy em ondas e cobrança mensal."],
        "tags": ["fastapi", "docker", "nginx", "github actions", "rate limit"],
    },
    {
        "arquivo": "projeto-plog", "numero": "03", "titulo": "PLog",
        "status": "público ↗", "cor": "azul",
        "descricao": ["consulta de flows nat (cgnat) para o noc: quem usava",
                      "este ip, nesta porta, naquele instante."],
        "tags": ["fastapi", "paramiko", "pydantic", "sqlite", "jwt"],
    },
]

STACK = [
    ("frontend", [("react", "React"), ("typescript", "TypeScript"), ("javascript", "JavaScript"),
                  ("tailwindcss", "Tailwind"), ("reactquery", "TanStack Query"), ("figma", "Figma")]),
    ("backend", [("python", "Python"), ("fastapi", "FastAPI"), ("django", "Django"),
                 ("flask", "Flask"), ("pydantic", "Pydantic"), ("pytest", "Pytest")]),
    ("banco de dados", [("postgresql", "PostgreSQL"), ("sqlite", "SQLite"), ("sqlalchemy", "SQLAlchemy")]),
    ("segurança", [("jsonwebtokens", "JWT"), ("argon2id", "Argon2id"), ("ratelimit", "Rate limit"),
                   ("cabecalhos", "CSP · HSTS"), ("segredos", "Segredos cifrados"), ("auditoria", "Auditoria")]),
    ("resiliência", [("circuitbreaker", "Circuit breaker"), ("timeouts", "Timeouts"),
                     ("retries", "Retries com backoff"), ("idempotencia", "Idempotência")]),
    ("ia", [("claude", "Claude"), ("openai", "OpenAI"), ("opencv", "OpenCV")]),
    ("infra", [("docker", "Docker"), ("portainer", "Portainer"), ("coolify", "Coolify"), ("nginx", "NGINX"),
               ("linux", "Linux"), ("githubactions", "GitHub Actions"), ("gitlab", "GitLab"),
               ("amazonwebservices", "AWS"), ("kubernetes", "Kubernetes")]),
]

MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]

# ---------------------------------------------------------------- desenho


def largura_mono(texto: str, tamanho: float) -> float:
    """Fonte de código tem todas as letras da mesma largura: ~0,61 do tamanho."""
    return len(texto) * tamanho * 0.61


def largura_sans(texto: str, tamanho: float, negrito: bool = False) -> float:
    """Estimativa letra a letra (maiúscula é mais larga); a fonte do sistema varia,
    então a conta erra para mais, sobrando folga em vez de faltar."""
    def letra(c: str) -> float:
        if c.isupper():
            return 0.7
        if c.isdigit():
            return 0.58
        if c in " .,:;!|'%":
            return 0.32 if c != "%" else 0.85
        return 0.54
    return sum(letra(c) for c in texto) * tamanho * (1.06 if negrito else 1)


def texto(x, y, conteudo, tamanho, cor, fonte=SANS, peso=400, ancora="start") -> str:
    return (f'<text x="{x:g}" y="{y:g}" font-family="{fonte}" font-size="{tamanho}" '
            f'font-weight="{peso}" fill="{cor}" text-anchor="{ancora}">{escape(conteudo)}</text>')


def svg(largura, altura, corpo, titulo) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{largura}" height="{altura:g}" '
            f'viewBox="0 0 {largura} {altura:g}" role="img" aria-label="{escape(titulo)}">'
            f'<title>{escape(titulo)}</title>{"".join(corpo)}</svg>\n')


def cartao(largura, altura, t) -> str:
    return (f'<rect x="0.5" y="0.5" width="{largura - 1}" height="{altura - 1:g}" rx="12" '
            f'fill="{t["fundo"]}" stroke="{t["borda"]}"/>')


def escuro_demais(cor: str) -> bool:
    r, g, b = (int(cor[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b < 0.25


def icone(slug, x, y, tamanho, tema) -> str:
    """Ícone de marca na cor dela; no tema escuro, marca escura demais vira clara."""
    i = ICONES[slug]
    abre = f'<svg x="{x:g}" y="{y:g}" width="{tamanho}" height="{tamanho}" viewBox="{i["vb"]}">'
    if i["tipo"] == "marca":
        cor = i["cor"]
        if tema == "escuro" and escuro_demais(cor):
            cor = TEMAS["escuro"]["tinta"]
        return f'{abre}<path fill="{cor}" d="{i["d"]}"/></svg>'
    if i["tipo"] == "traco":
        cor = i["cor_escuro"] if tema == "escuro" else i["cor"]
        return (f'{abre}<g fill="none" stroke="{cor}" stroke-width="2" stroke-linecap="round" '
                f'stroke-linejoin="round">{i["corpo"]}</g></svg>')
    corpo = i.get("corpo_escuro", i["corpo"]) if tema == "escuro" else i["corpo"]
    return f"{abre}{corpo}</svg>"


def pilula(x, y, rotulo, t, tema, slug=None, altura=24, fonte=12) -> tuple[str, float]:
    """Uma etiqueta arredondada; devolve o desenho e a largura dela."""
    esq, dir_, vao, tam_ic = (12, 14, 8, 16) if slug else (10, 10, 0, 0)
    largura = esq + tam_ic + vao + largura_mono(rotulo, fonte) + dir_
    partes = [f'<rect x="{x + 0.5:g}" y="{y + 0.5:g}" width="{largura - 1:g}" height="{altura - 1}" '
              f'rx="{altura / 2:g}" fill="{t["pilula"]}" stroke="{t["borda"]}"/>']
    if slug:
        partes.append(icone(slug, x + esq, y + (altura - tam_ic) / 2, tam_ic, tema))
    partes.append(texto(x + esq + tam_ic + vao, y + altura / 2 + fonte * 0.36, rotulo, fonte,
                        t["tinta"], MONO))
    return "".join(partes), largura


def fluxo(itens, x0, largura_max, gerar, altura, vao=8) -> tuple[list[str], float]:
    """Arruma pílulas em linhas que quebram; devolve o desenho e a altura ocupada."""
    partes, x, y = [], x0, 0.0
    for item in itens:
        _, larg = gerar(0, 0, item)
        if x > x0 and x + larg > x0 + largura_max:
            x, y = x0, y + altura + vao
        desenho, larg = gerar(x, y, item)
        partes.append(desenho)
        x += larg + vao
    return partes, y + altura


def deslocar(partes: list[str], dy: float) -> str:
    return f'<g transform="translate(0 {dy:g})">{"".join(partes)}</g>'


def desenhar_projeto(p, tema) -> str:
    t, L = TEMAS[tema], 420
    corpo = [texto(24, 36, p["numero"], 12, t["fraco"], MONO)]
    cor = t[p["cor"]]
    corpo.append(texto(L - 24, 36, p["status"], 12, cor, MONO, ancora="end"))
    corpo.append(f'<circle cx="{L - 24 - largura_mono(p["status"], 12) - 10:g}" cy="32" r="4" fill="{cor}"/>')
    corpo.append(texto(24, 74, p["titulo"], 22, t["tinta"], peso=600))
    for i, linha in enumerate(p["descricao"]):
        corpo.append(texto(24, 104 + i * 21, linha, 14, t["fraco"]))
    tags, altura_tags = fluxo(p["tags"], 24, L - 48,
                              lambda x, y, rot: pilula(x, y, rot, t, tema), 24)
    topo_tags = 104 + 21 * (len(p["descricao"]) - 1) + 20
    altura = topo_tags + altura_tags + 24
    return svg(L, altura, [cartao(L, altura, t), *corpo, deslocar(tags, topo_tags)],
               f'{p["titulo"]}: {" ".join(p["descricao"])}')


def desenhar_stack(tema) -> str:
    t, L = TEMAS[tema], 836
    x_pilulas, alt = 200, 30
    corpo, y = [], 8.0
    for n, (rotulo, itens) in enumerate(STACK):
        pilulas, altura = fluxo(itens, x_pilulas, L - 24 - x_pilulas,
                                lambda x, yy, it: pilula(x, yy, it[1], t, tema, it[0], alt, 13), alt)
        topo = y + 12
        corpo.append(texto(24, topo + altura / 2 + 4.5, rotulo, 13, t["fraco"], MONO))
        corpo.append(deslocar(pilulas, topo))
        y = topo + altura + 12
        if n < len(STACK) - 1:
            corpo.append(f'<line x1="24" x2="{L - 24}" y1="{y:g}" y2="{y:g}" stroke="{t["tracejado"]}" '
                         f'stroke-dasharray="3 3"/>')
    altura = y + 8
    nomes = ", ".join(nome for _, itens in STACK for _, nome in itens)
    return svg(L, altura, [cartao(L, altura, t), *corpo], f"stack: {nomes}")


def numero_br(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def desenhar_estatisticas(dados, tema) -> str:
    t, L = TEMAS[tema], 836
    corpo = [texto(24, 34, "últimos 12 meses", 12, t["fraco"], MONO),
             texto(L - 24, 34, f'atualizado em {dados["atualizado"]}', 12, t["fraco"], MONO, ancora="end")]
    numeros = [(dados["contribuicoes"], "contribuições"), (dados["commits"], "commits"),
               (dados["prs"], "pull requests"), (dados["repositorios"], "repositórios")]
    for i, (valor, rotulo) in enumerate(numeros):
        x = 24 + i * 197
        corpo.append(texto(x, 80, numero_br(valor), 28, t["tinta"], peso=600))
        corpo.append(texto(x, 102, rotulo, 12, t["fraco"], MONO))

    gx, gy, passo, lado = 56, 150, 14, 11
    ultima_col = -9
    for col, semana in enumerate(dados["semanas"]):
        for dia in semana:
            linha = dia["dia_semana"]
            corpo.append(f'<rect x="{gx + col * passo}" y="{gy + linha * passo}" width="{lado}" '
                         f'height="{lado}" rx="2" fill="{t["niveis"][dia["nivel"]]}"/>')
            data = dt.date.fromisoformat(dia["data"])
            if data.day == 1 and col - ultima_col >= 3 and col > 0:
                corpo.append(texto(gx + col * passo, gy - 8, MESES[data.month - 1], 11, t["fraco"]))
                ultima_col = col
    for rotulo, linha in (("seg", 1), ("qua", 3), ("sex", 5)):
        corpo.append(texto(24, gy + linha * passo + 9, rotulo, 11, t["fraco"]))
    base = gy + 7 * passo + 14
    corpo.append(texto(gx, base, "contribuições contam commits, pull requests e issues, inclusive em "
                       "repositórios privados", 11, t["fraco"]))
    fim = gx + len(dados["semanas"]) * passo - 3
    x = fim - largura_sans("mais", 11)
    corpo.append(texto(x, base, "mais", 11, t["fraco"]))
    x -= 4 + 5 * (lado + 3)
    for nivel in range(5):
        corpo.append(f'<rect x="{x + nivel * (lado + 3):g}" y="{base - 9}" width="{lado}" height="{lado}" '
                     f'rx="2" fill="{t["niveis"][nivel]}"/>')
    corpo.append(texto(x - 4, base, "menos", 11, t["fraco"], ancora="end"))

    yb, largura_barra = base + 22, L - 48
    corpo.append(f'<clipPath id="barra-{tema}"><rect x="24" y="{yb}" width="{largura_barra}" '
                 f'height="8" rx="4"/></clipPath><g clip-path="url(#barra-{tema})">')
    x = 24.0
    for nome, pct, cor in dados["linguagens"]:
        larg = largura_barra * pct / 100
        corpo.append(f'<rect x="{x:g}" y="{yb}" width="{max(larg - 2, 1):g}" height="8" fill="{cor}"/>')
        x += larg
    corpo.append("</g>")
    x, yl = 24.0, yb + 30
    for nome, pct, cor in dados["linguagens"]:
        valor = f"{pct:.1f}".replace(".", ",").replace(",0", "") + "%"
        corpo.append(f'<circle cx="{x + 4:g}" cy="{yl - 4}" r="4" fill="{cor}"/>')
        # nome e percentual no mesmo <text>: o navegador encosta um no outro sozinho
        corpo.append(f'<text x="{x + 14:g}" y="{yl}" font-family="{SANS}" font-size="12" fill="{t["tinta"]}">'
                     f'<tspan font-weight="600">{escape(nome)}</tspan>'
                     f'<tspan fill="{t["fraco"]}"> {valor}</tspan></text>')
        x += 14 + largura_sans(nome, 12, True) + largura_sans(" " + valor, 12) + 20
    altura = yl + 24
    resumo = (f'{numero_br(dados["contribuicoes"])} contribuições, {numero_br(dados["commits"])} commits e '
              f'{dados["prs"]} pull requests nos últimos 12 meses')
    return svg(L, altura, [cartao(L, altura, t), *corpo], resumo)


# ---------------------------------------------------------------- dados


def graphql(token: str, consulta: str, variaveis: dict | None = None) -> dict:
    """Chama a API com tempo limite e até 3 tentativas, esperando 2 s, 4 s entre elas."""
    corpo = json.dumps({"query": consulta, "variables": variaveis or {}}).encode()
    pedido = urllib.request.Request("https://api.github.com/graphql", data=corpo, headers={
        "Authorization": f"bearer {token}", "User-Agent": "readme-do-perfil"})
    for tentativa in range(3):
        try:
            with urllib.request.urlopen(pedido, timeout=30) as resposta:
                dados = json.load(resposta)
            if dados.get("errors"):
                raise RuntimeError(dados["errors"])
            return dados["data"]
        except (urllib.error.URLError, TimeoutError) as erro:
            if isinstance(erro, urllib.error.HTTPError) and erro.code < 500 or tentativa == 2:
                raise
            time.sleep(2 ** (tentativa + 1))
    raise AssertionError("inalcançável")


CONSULTA_PERFIL = """
query($login: String!) {
  user(login: $login) {
    id
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date weekday contributionLevel } }
      }
    }
    repositories(ownerAffiliations: OWNER, isFork: false, first: 100) {
      totalCount
      nodes {
        name
        languages(first: 20) { edges { size node { name color } } }
      }
    }
    repositoriesContributedTo(first: 100, includeUserRepositories: false,
                              contributionTypes: [COMMIT, PULL_REQUEST]) {
      nodes { nameWithOwner }
    }
  }
}"""

NIVEIS = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}


def buscar(token: str) -> dict:
    hoje = dt.datetime.now(dt.timezone.utc)
    desde = hoje - dt.timedelta(days=365)
    perfil = graphql(token, CONSULTA_PERFIL, {"login": USUARIO})["user"]
    calendario = perfil["contributionsCollection"]["contributionCalendar"]
    repos = perfil["repositories"]["nodes"]

    # A API resume os privados como "contribuições restritas"; o total de commits
    # sai do histórico de cada repositório (os próprios e os de terceiros em que ele
    # contribui), contando só os commits deste usuário.
    alvos = [(USUARIO, r["name"]) for r in repos] + [
        tuple(r["nameWithOwner"].split("/", 1)) for r in perfil["repositoriesContributedTo"]["nodes"]]
    apelidos = "\n".join(
        f'r{i}: repository(owner: "{dono}", name: "{nome}") {{ defaultBranchRef {{ target {{ '
        f'... on Commit {{ history(since: $desde, author: {{id: $id}}) {{ totalCount }} }} }} }} }}'
        for i, (dono, nome) in enumerate(alvos))
    historicos = graphql(token, f"query($desde: GitTimestamp!, $id: ID!) {{ {apelidos} }}",
                         {"desde": desde.isoformat(), "id": perfil["id"]})
    def contar(repo: dict | None) -> int:  # repositório vazio não tem branch: conta zero
        alvo = ((repo or {}).get("defaultBranchRef") or {}).get("target") or {}
        return (alvo.get("history") or {}).get("totalCount", 0)

    commits = sum(contar(h) for h in historicos.values())

    busca = f"author:{USUARIO} is:pr created:>={desde.date().isoformat()}"
    prs = graphql(token, "query($q: String!) { search(query: $q, type: ISSUE, first: 1) { issueCount } }",
                  {"q": busca})["search"]["issueCount"]

    tamanhos: dict[str, list] = {}
    for r in repos:
        for aresta in r["languages"]["edges"]:
            nome = aresta["node"]["name"]
            tamanhos.setdefault(nome, [0, aresta["node"]["color"] or "#8c959f"])[0] += aresta["size"]
    total = sum(v[0] for v in tamanhos.values()) or 1
    ordem = sorted(tamanhos.items(), key=lambda kv: -kv[1][0])
    linguagens = [(nome, round(100 * v[0] / total, 1), v[1]) for nome, v in ordem[:5]]
    resto = round(100 - sum(p for _, p, _ in linguagens), 1)
    if resto > 0:
        linguagens.append(("outras", resto, "#8c959f"))

    semanas = [[{"data": d["date"], "dia_semana": d["weekday"], "nivel": NIVEIS[d["contributionLevel"]]}
                for d in s["contributionDays"]] for s in calendario["weeks"]]
    return {
        "atualizado": hoje.astimezone(dt.timezone(dt.timedelta(hours=-3))).strftime("%d/%m/%Y"),
        "contribuicoes": calendario["totalContributions"], "commits": commits, "prs": prs,
        "repositorios": perfil["repositories"]["totalCount"] + len(perfil["repositoriesContributedTo"]["nodes"]),
        "semanas": semanas, "linguagens": linguagens,
    }


# ---------------------------------------------------------------- saída


def gravar(nome: str, conteudo: str) -> None:
    (ASSETS / nome).write_text(conteudo, encoding="utf-8", newline="\n")


def main() -> None:
    ASSETS.mkdir(exist_ok=True)
    for tema in TEMAS:
        for p in PROJETOS:
            gravar(f'{p["arquivo"]}-{tema}.svg', desenhar_projeto(p, tema))
        gravar(f"stack-{tema}.svg", desenhar_stack(tema))
    token = os.environ.get("GH_TOKEN")
    if not token:
        print("sem GH_TOKEN: estatísticas mantidas como estão")
        return
    dados = buscar(token)
    for tema in TEMAS:
        gravar(f"estatisticas-{tema}.svg", desenhar_estatisticas(dados, tema))
    print(f'{dados["contribuicoes"]} contribuições, {dados["commits"]} commits, {dados["prs"]} PRs, '
          f'{dados["repositorios"]} repositórios')


if __name__ == "__main__":
    main()
