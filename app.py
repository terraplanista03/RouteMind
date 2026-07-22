import logging
import traceback
from uuid import uuid4

from fastapi import FastAPI, Form, Request
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from services.excel_service import ExcelService
from services.pdf_service import PDFService
from services.route_service import RouteService
from services.share_service import ShareService


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger("RouteMind")


app = FastAPI(
    title="RouteMind",
    description="Otimizador Inteligente de Rotas",
    version="2.0"
)

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)

templates = Jinja2Templates(
    directory="templates"
)

route_service = RouteService()
excel_service = ExcelService()
pdf_service = PDFService()
share_service = ShareService()

resultados_gerados = {}


def buscar_resultado(
    resultado_id: str
):

    return resultados_gerados.get(
        resultado_id
    )


def contexto_resultado(
    request: Request,
    resultado_id: str,
    resultado: dict,
    compartilhado: bool = False
):

    return {
        "request": request,
        "titulo": "Resultado - RouteMind",
        "origem": resultado["origem"],
        "origem_dados": resultado["origem_dados"],
        "entregas": resultado["entregas"],
        "analise": resultado["analise"],
        "rotas": resultado["rotas"],
        "resultado_id": resultado_id,
        "link_compartilhamento": share_service.gerar_link(
            resultado_id
        ),
        "compartilhado": compartilhado
    }


def pagina_resultado_nao_encontrado(
    request: Request
):

    return templates.TemplateResponse(
        request=request,
        name="erro.html",
        context={
            "request": request,
            "mensagem": (
                "O resultado solicitado não foi encontrado. "
                "Gere as rotas novamente."
            ),
            "detalhes": None
        },
        status_code=404
    )


@app.get("/")
async def home(
    request: Request
):

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "request": request,
            "titulo": "RouteMind"
        }
    )


@app.post("/gerar")
async def gerar_rotas(
    request: Request,
    origem: str = Form(...),
    enderecos: str = Form(...)
):

    try:

        origem = origem.strip()

        if not origem:

            raise ValueError(
                "Informe um endereço de origem."
            )

        lista_enderecos = [
            endereco.strip()
            for endereco in enderecos.splitlines()
            if endereco.strip()
        ]

        if not lista_enderecos:

            raise ValueError(
                "Informe pelo menos um endereço de entrega."
            )

        logger.info(
            "Gerando rotas para %s entregas.",
            len(lista_enderecos)
        )

        (
            origem_dados,
            entregas,
            matriz,
            analise,
            rotas
        ) = route_service.processar(
            origem,
            "\n".join(lista_enderecos)
        )

        resultado_id = str(
            uuid4()
        )

        resultado = {
            "origem": origem,
            "origem_dados": origem_dados,
            "entregas": entregas,
            "analise": analise,
            "rotas": rotas
        }

        resultados_gerados[
            resultado_id
        ] = resultado

        logger.info(
            "Rotas geradas com sucesso. Identificador: %s",
            resultado_id
        )

        return templates.TemplateResponse(
            request=request,
            name="resultado.html",
            context=contexto_resultado(
                request=request,
                resultado_id=resultado_id,
                resultado=resultado
            )
        )

    except ValueError as erro:

        logger.warning(
            "Erro de validação: %s",
            erro
        )

        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "request": request,
                "titulo": "RouteMind",
                "erro": str(erro),
                "origem": origem,
                "enderecos": enderecos
            },
            status_code=400
        )

    except Exception as erro:

        logger.exception(
            "Erro inesperado durante a geração das rotas."
        )

        return templates.TemplateResponse(
            request=request,
            name="erro.html",
            context={
                "request": request,
                "mensagem": str(erro),
                "detalhes": traceback.format_exc()
            },
            status_code=500
        )


@app.get(
    "/rota/{resultado_id}"
)
async def visualizar_rota_compartilhada(
    request: Request,
    resultado_id: str
):

    try:

        resultado = buscar_resultado(
            resultado_id
        )

        if not resultado:

            return pagina_resultado_nao_encontrado(
                request
            )

        logger.info(
            "Visualizando rota compartilhada: %s",
            resultado_id
        )

        return templates.TemplateResponse(
            request=request,
            name="resultado.html",
            context=contexto_resultado(
                request=request,
                resultado_id=resultado_id,
                resultado=resultado,
                compartilhado=True
            )
        )

    except Exception as erro:

        logger.exception(
            "Erro ao visualizar a rota compartilhada."
        )

        return templates.TemplateResponse(
            request=request,
            name="erro.html",
            context={
                "request": request,
                "mensagem": str(erro),
                "detalhes": traceback.format_exc()
            },
            status_code=500
        )


@app.get(
    "/exportar/excel/{resultado_id}"
)
async def exportar_excel(
    request: Request,
    resultado_id: str
):

    try:

        resultado = buscar_resultado(
            resultado_id
        )

        if not resultado:

            return pagina_resultado_nao_encontrado(
                request
            )

        arquivo = excel_service.gerar(
            resultado["origem"],
            resultado["analise"],
            resultado["rotas"]
        )

        nome_arquivo = (
            f"rotas_{resultado_id[:8]}.xlsx"
        )

        logger.info(
            "Exportando arquivo Excel: %s",
            nome_arquivo
        )

        return StreamingResponse(
            arquivo,
            media_type=(
                "application/vnd.openxmlformats-"
                "officedocument.spreadsheetml.sheet"
            ),
            headers={
                "Content-Disposition": (
                    f'attachment; filename="{nome_arquivo}"'
                )
            }
        )

    except Exception as erro:

        logger.exception(
            "Erro ao exportar o arquivo Excel."
        )

        return templates.TemplateResponse(
            request=request,
            name="erro.html",
            context={
                "request": request,
                "mensagem": str(erro),
                "detalhes": traceback.format_exc()
            },
            status_code=500
        )


@app.get(
    "/exportar/pdf/{resultado_id}"
)
async def exportar_pdf(
    request: Request,
    resultado_id: str
):

    try:

        resultado = buscar_resultado(
            resultado_id
        )

        if not resultado:

            return pagina_resultado_nao_encontrado(
                request
            )

        arquivo = pdf_service.gerar(
            resultado["origem"],
            resultado["analise"],
            resultado["rotas"]
        )

        nome_arquivo = (
            f"rotas_{resultado_id[:8]}.pdf"
        )

        logger.info(
            "Exportando arquivo PDF: %s",
            nome_arquivo
        )

        return StreamingResponse(
            arquivo,
            media_type="application/pdf",
            headers={
                "Content-Disposition": (
                    f'attachment; filename="{nome_arquivo}"'
                )
            }
        )

    except Exception as erro:

        logger.exception(
            "Erro ao exportar o arquivo PDF."
        )

        return templates.TemplateResponse(
            request=request,
            name="erro.html",
            context={
                "request": request,
                "mensagem": str(erro),
                "detalhes": traceback.format_exc()
            },
            status_code=500
        )