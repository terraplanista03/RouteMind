from models.delivery import Delivery


class Validator:

    @staticmethod
    def criar_lista(texto: str):

        entregas = []

        linhas = texto.split("\n")

        for linha in linhas:

            linha = linha.strip()

            if linha:

                entregas.append(
                    Delivery(endereco=linha)
                )

        return entregas