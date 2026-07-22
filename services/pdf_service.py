from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle
)


class PDFService:

    def gerar(
        self,
        origem,
        analise,
        rotas
    ):

        arquivo = BytesIO()

        documento = SimpleDocTemplate(
            arquivo,
            pagesize=A4,
            rightMargin=1.5 * cm,
            leftMargin=1.5 * cm,
            topMargin=1.5 * cm,
            bottomMargin=1.5 * cm,
            title="Rotas - RouteMind",
            author="RouteMind"
        )

        estilos = getSampleStyleSheet()

        estilo_titulo = ParagraphStyle(
            name="TituloRouteMind",
            parent=estilos["Title"],
            alignment=TA_CENTER,
            fontSize=22,
            leading=26,
            textColor=colors.HexColor("#1D4ED8"),
            spaceAfter=12
        )

        estilo_subtitulo = ParagraphStyle(
            name="SubtituloRouteMind",
            parent=estilos["Heading2"],
            fontSize=16,
            leading=20,
            textColor=colors.HexColor("#1F2937"),
            spaceBefore=10,
            spaceAfter=10
        )

        estilo_texto = ParagraphStyle(
            name="TextoRouteMind",
            parent=estilos["BodyText"],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#374151")
        )

        estilo_endereco = ParagraphStyle(
            name="EnderecoRouteMind",
            parent=estilo_texto,
            fontSize=9,
            leading=12
        )

        elementos = []

        elementos.append(
            Paragraph(
                "RouteMind",
                estilo_titulo
            )
        )

        elementos.append(
            Paragraph(
                "Relatório de rotas otimizadas",
                estilo_texto
            )
        )

        elementos.append(
            Spacer(
                1,
                0.5 * cm
            )
        )

        elementos.append(
            Paragraph(
                "Origem",
                estilo_subtitulo
            )
        )

        elementos.append(
            Paragraph(
                self._texto_seguro(origem),
                estilo_texto
            )
        )

        elementos.append(
            Spacer(
                1,
                0.5 * cm
            )
        )

        resumo = [
            [
                "Motoristas",
                "Distância total",
                "Deslocamento",
                "Tempo total"
            ],
            [
                str(
                    analise.get(
                        "motoristas",
                        0
                    )
                ),
                (
                    f"{analise.get('distancia_total_km', 0)} km"
                ),
                (
                    f"{analise.get('tempo_deslocamento', 0)} min"
                ),
                (
                    f"{analise.get('tempo_total', 0)} min"
                )
            ]
        ]

        tabela_resumo = Table(
            resumo,
            colWidths=[
                4 * cm,
                4 * cm,
                4 * cm,
                4 * cm
            ],
            repeatRows=1
        )

        tabela_resumo.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.HexColor("#2563EB")
                    ),
                    (
                        "TEXTCOLOR",
                        (0, 0),
                        (-1, 0),
                        colors.white
                    ),
                    (
                        "FONTNAME",
                        (0, 0),
                        (-1, 0),
                        "Helvetica-Bold"
                    ),
                    (
                        "ALIGN",
                        (0, 0),
                        (-1, -1),
                        "CENTER"
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "MIDDLE"
                    ),
                    (
                        "BACKGROUND",
                        (0, 1),
                        (-1, -1),
                        colors.HexColor("#F9FAFB")
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.5,
                        colors.HexColor("#D1D5DB")
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        8
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        8
                    )
                ]
            )
        )

        elementos.append(
            tabela_resumo
        )

        elementos.append(
            Spacer(
                1,
                0.6 * cm
            )
        )

        estatisticas = {
            item.get("motorista"): item
            for item in analise.get(
                "rotas",
                []
            )
        }

        for indice_rota, rota in enumerate(
            rotas
        ):

            numero_motorista = rota.get(
                "motorista",
                indice_rota + 1
            )

            estatistica = estatisticas.get(
                numero_motorista,
                {}
            )

            elementos.append(
                Paragraph(
                    (
                        f"Motorista "
                        f"{numero_motorista}"
                    ),
                    estilo_subtitulo
                )
            )

            resumo_motorista = [
                [
                    "Entregas",
                    "Distância",
                    "Deslocamento",
                    "Paradas",
                    "Tempo total"
                ],
                [
                    str(
                        estatistica.get(
                            "entregas",
                            0
                        )
                    ),
                    (
                        f"{estatistica.get('distancia_km', 0)} km"
                    ),
                    (
                        f"{estatistica.get('tempo_deslocamento', 0)} min"
                    ),
                    (
                        f"{estatistica.get('tempo_paradas', 0)} min"
                    ),
                    (
                        f"{estatistica.get('tempo_total', 0)} min"
                    )
                ]
            ]

            tabela_motorista = Table(
                resumo_motorista,
                colWidths=[
                    3.2 * cm,
                    3.2 * cm,
                    3.2 * cm,
                    3.2 * cm,
                    3.2 * cm
                ],
                repeatRows=1
            )

            tabela_motorista.setStyle(
                TableStyle(
                    [
                        (
                            "BACKGROUND",
                            (0, 0),
                            (-1, 0),
                            colors.HexColor("#E5E7EB")
                        ),
                        (
                            "FONTNAME",
                            (0, 0),
                            (-1, 0),
                            "Helvetica-Bold"
                        ),
                        (
                            "ALIGN",
                            (0, 0),
                            (-1, -1),
                            "CENTER"
                        ),
                        (
                            "VALIGN",
                            (0, 0),
                            (-1, -1),
                            "MIDDLE"
                        ),
                        (
                            "GRID",
                            (0, 0),
                            (-1, -1),
                            0.5,
                            colors.HexColor("#D1D5DB")
                        ),
                        (
                            "TOPPADDING",
                            (0, 0),
                            (-1, -1),
                            7
                        ),
                        (
                            "BOTTOMPADDING",
                            (0, 0),
                            (-1, -1),
                            7
                        )
                    ]
                )
            )

            elementos.append(
                tabela_motorista
            )

            elementos.append(
                Spacer(
                    1,
                    0.4 * cm
                )
            )

            dados_entregas = [
                [
                    "Parada",
                    "Endereço",
                    "Bairro",
                    "Cidade"
                ]
            ]

            numero_parada = 1

            for ponto in rota.get(
                "roteiro",
                []
            ):

                if ponto.get(
                    "tipo"
                ) != "Entrega":

                    continue

                dados_entregas.append(
                    [
                        str(numero_parada),
                        Paragraph(
                            self._texto_seguro(
                                ponto.get(
                                    "endereco"
                                )
                            ),
                            estilo_endereco
                        ),
                        Paragraph(
                            self._texto_seguro(
                                ponto.get(
                                    "bairro"
                                )
                            ),
                            estilo_endereco
                        ),
                        Paragraph(
                            self._texto_seguro(
                                ponto.get(
                                    "cidade"
                                )
                            ),
                            estilo_endereco
                        )
                    ]
                )

                numero_parada += 1

            dados_entregas.append(
                [
                    "Retorno",
                    Paragraph(
                        self._texto_seguro(
                            origem
                        ),
                        estilo_endereco
                    ),
                    "",
                    ""
                ]
            )

            tabela_entregas = Table(
                dados_entregas,
                colWidths=[
                    1.7 * cm,
                    8 * cm,
                    3.2 * cm,
                    3.2 * cm
                ],
                repeatRows=1
            )

            tabela_entregas.setStyle(
                TableStyle(
                    [
                        (
                            "BACKGROUND",
                            (0, 0),
                            (-1, 0),
                            colors.HexColor("#2563EB")
                        ),
                        (
                            "TEXTCOLOR",
                            (0, 0),
                            (-1, 0),
                            colors.white
                        ),
                        (
                            "FONTNAME",
                            (0, 0),
                            (-1, 0),
                            "Helvetica-Bold"
                        ),
                        (
                            "ALIGN",
                            (0, 0),
                            (0, -1),
                            "CENTER"
                        ),
                        (
                            "VALIGN",
                            (0, 0),
                            (-1, -1),
                            "MIDDLE"
                        ),
                        (
                            "GRID",
                            (0, 0),
                            (-1, -1),
                            0.5,
                            colors.HexColor("#D1D5DB")
                        ),
                        (
                            "ROWBACKGROUNDS",
                            (0, 1),
                            (-1, -2),
                            [
                                colors.white,
                                colors.HexColor("#F9FAFB")
                            ]
                        ),
                        (
                            "BACKGROUND",
                            (0, -1),
                            (-1, -1),
                            colors.HexColor("#DBEAFE")
                        ),
                        (
                            "FONTNAME",
                            (0, -1),
                            (0, -1),
                            "Helvetica-Bold"
                        ),
                        (
                            "TOPPADDING",
                            (0, 0),
                            (-1, -1),
                            7
                        ),
                        (
                            "BOTTOMPADDING",
                            (0, 0),
                            (-1, -1),
                            7
                        )
                    ]
                )
            )

            elementos.append(
                tabela_entregas
            )

            if indice_rota < len(rotas) - 1:

                elementos.append(
                    PageBreak()
                )

        documento.build(
            elementos,
            onFirstPage=self._adicionar_rodape,
            onLaterPages=self._adicionar_rodape
        )

        arquivo.seek(0)

        return arquivo

    @staticmethod
    def _texto_seguro(valor):

        if valor is None:

            return "Não informado"

        texto = str(
            valor
        ).strip()

        if not texto:

            return "Não informado"

        return (
            texto
            .replace(
                "&",
                "&amp;"
            )
            .replace(
                "<",
                "&lt;"
            )
            .replace(
                ">",
                "&gt;"
            )
        )

    @staticmethod
    def _adicionar_rodape(
        canvas,
        documento
    ):

        canvas.saveState()

        canvas.setFont(
            "Helvetica",
            8
        )

        canvas.setFillColor(
            colors.HexColor("#6B7280")
        )

        canvas.drawString(
            1.5 * cm,
            0.8 * cm,
            "RouteMind - Relatório de rotas"
        )

        canvas.drawRightString(
            A4[0] - 1.5 * cm,
            0.8 * cm,
            f"Página {documento.page}"
        )

        canvas.restoreState()