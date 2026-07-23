import logging
import os
import traceback
from collections import OrderedDict
from threading import Lock
from uuid import uuid4

from fastapi import FastAPI
from fastapi import Form
from fastapi import Request
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from services.excel_service import ExcelService
from services.pdf_service import PDFService
from services.route_service import RouteProcessingError
from services.route_service import RouteService
from services.share_service import ShareService


logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s | %(levelname)s | "
        "%(name)s | %(message)s"
    )
)

logger = logging.getLogger(
    "RouteMind"
)


class ResultStore:

    def __init__(
        self,
        max_items: int = 200
    ):

        self.max_items = max_items
        self.data = OrderedDict()
        self.lock = Lock()

    def save(
        self,
        result: dict
    ) -> str:

        result_id = str(
            uuid4()
        )

        with self.lock:

            self.data[
                result_id
            ] = result

            self.data.move_to_end(
                result_id
            )

            while len(
                self.data
            ) > self.max_items:

                self.data.popitem(
                    last=False
                )

        return result_id

    def get(
        self,
        result_id: str
    ) -> dict | None:

        with self.lock:

            result = self.data.get(
                result_id
            )

            if result is not None:

                self.data.move_to_end(
                    result_id
                )

            return result


app = FastAPI(
    title="RouteMind",
    description="Otimizador inteligente de rotas",
    version="3.0"
)

app.mount(
    "/static",
    StaticFiles(
        directory="static"
    ),
    name="static"
)

templates = Jinja2Templates(
    directory="templates"
)

route_service = RouteService()
excel_service = ExcelService()
pdf_service = PDFService()
share_service = ShareService()

result_store = ResultStore(
    max_items=200
)

SHOW_TECHNICAL_DETAILS = (
    os.getenv(
        "SHOW_TECHNICAL_DETAILS",
        "false"
    ).lower()
    == "true"
)


def render_error(
    request: Request,
    message: str,
    status_code: int = 400,
    error: Exception | None = None
):

    technical_details = None

    if (
        SHOW_TECHNICAL_DETAILS
        and error is not None
    ):

        technical_details = "".join(
            traceback.format_exception(
                type(error),
                error,
                error.__traceback__
            )
        )

    return templates.TemplateResponse(
        request=request,
        name="erro.html",
        context={
            "request": request,
            "mensagem": message,
            "detalhes": technical_details
        },
        status_code=status_code
    )


def render_not_found(
    request: Request
):

    return render_error(
        request=request,
        message=(
            "O resultado solicitado não foi encontrado. "
            "Gere as rotas novamente."
        ),
        status_code=404
    )


def build_result_context(
    request: Request,
    result_id: str,
    result: dict,
    shared: bool = False
) -> dict:

    return {
        "request": request,
        "titulo": "Resultado - RouteMind",
        "origem": result["origem"],
        "origem_dados": result["origem_dados"],
        "entregas": result["entregas"],
        "analise": result["analise"],
        "rotas": result["rotas"],
        "resultado_id": result_id,
        "link_compartilhamento": (
            share_service.gerar_link(
                result_id
            )
        ),
        "compartilhado": shared
    }


@app.exception_handler(
    404
)
async def not_found_handler(
    request: Request,
    _
):

    return render_not_found(
        request
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

    origem = str(
        origem or ""
    ).strip()

    enderecos = str(
        enderecos or ""
    ).strip()

    try:

        if not origem:

            raise RouteProcessingError(
                "Informe o endereço de origem."
            )

        lista_enderecos = [
            linha.strip()
            for linha in enderecos.splitlines()
            if linha.strip()
        ]

        if not lista_enderecos:

            raise RouteProcessingError(
                "Informe pelo menos um endereço de entrega."
            )

        if len(
            lista_enderecos
        ) > 50:

            raise RouteProcessingError(
                "O limite atual é de 50 entregas por vez."
            )

        logger.info(
            "Gerando rotas para %s entregas.",
            len(
                lista_enderecos
            )
        )

        (
            origem_dados,
            entregas,
            matriz,
            analise,
            rotas
        ) = route_service.processar(
            origem=origem,
            enderecos="\n".join(
                lista_enderecos
            )
        )

        result = {
            "origem": origem,
            "origem_dados": origem_dados,
            "entregas": entregas,
            "matriz": matriz,
            "analise": analise,
            "rotas": rotas
        }

        result_id = result_store.save(
            result
        )

        logger.info(
            "Rotas geradas com sucesso: %s",
            result_id
        )

        return templates.TemplateResponse(
            request=request,
            name="resultado.html",
            context=build_result_context(
                request=request,
                result_id=result_id,
                result=result
            )
        )

    except RouteProcessingError as error:

        logger.warning(
            "Falha controlada: %s",
            error
        )

        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "request": request,
                "titulo": "RouteMind",
                "erro": str(
                    error
                ),
                "origem": origem,
                "enderecos": enderecos
            },
            status_code=400
        )

    except Exception as error:

        logger.exception(
            "Erro inesperado ao gerar as rotas."
        )

        return render_error(
            request=request,
            message=(
                "Ocorreu um erro inesperado durante o "
                "processamento. Tente novamente."
            ),
            status_code=500,
            error=error
        )


@app.get(
    "/rota/{resultado_id}"
)
async def visualizar_rota(
    request: Request,
    resultado_id: str
):

    result = result_store.get(
        resultado_id
    )

    if result is None:

        return render_not_found(
            request
        )

    return templates.TemplateResponse(
        request=request,
        name="resultado.html",
        context=build_result_context(
            request=request,
            result_id=resultado_id,
            result=result,
            shared=True
        )
    )


@app.get(
    "/exportar/excel/{resultado_id}"
)
async def exportar_excel(
    request: Request,
    resultado_id: str
):

    result = result_store.get(
        resultado_id
    )

    if result is None:

        return render_not_found(
            request
        )

    try:

        arquivo = excel_service.gerar(
            result["origem"],
            result["analise"],
            result["rotas"]
        )

        filename = (
            f"rotas_{resultado_id[:8]}.xlsx"
        )

        return StreamingResponse(
            arquivo,
            media_type=(
                "application/vnd.openxmlformats-"
                "officedocument.spreadsheetml.sheet"
            ),
            headers={
                "Content-Disposition": (
                    f'attachment; filename="{filename}"'
                )
            }
        )

    except Exception as error:

        logger.exception(
            "Erro ao exportar Excel."
        )

        return render_error(
            request=request,
            message=(
                "Não foi possível gerar o arquivo Excel."
            ),
            status_code=500,
            error=error
        )


@app.get(
    "/exportar/pdf/{resultado_id}"
)
async def exportar_pdf(
    request: Request,
    resultado_id: str
):

    result = result_store.get(
        resultado_id
    )

    if result is None:

        return render_not_found(
            request
        )

    try:

        arquivo = pdf_service.gerar(
            result["origem"],
            result["analise"],
            result["rotas"]
        )

        filename = (
            f"rotas_{resultado_id[:8]}.pdf"
        )

        return StreamingResponse(
            arquivo,
            media_type="application/pdf",
            headers={
                "Content-Disposition": (
                    f'attachment; filename="{filename}"'
                )
            }
        )

    except Exception as error:

        logger.exception(
            "Erro ao exportar PDF."
        )

        return render_error(
            request=request,
            message=(
                "Não foi possível gerar o arquivo PDF."
            ),
            status_code=500,
            error=error
        )


@app.get("/saude")
async def health_check():

    return {
        "status": "online",
        "aplicacao": "RouteMind",
        "versao": "3.0"
    }