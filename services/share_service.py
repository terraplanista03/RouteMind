import json
import base64


class ShareService:

    @staticmethod
    def gerar_link(resultado_id):

        return f"/rota/{resultado_id}"

    @staticmethod
    def exportar_json(dados):

        return json.dumps(
            dados,
            ensure_ascii=False,
            indent=4
        )

    @staticmethod
    def importar_json(texto):

        return json.loads(texto)

    @staticmethod
    def gerar_token(dados):

        texto = json.dumps(
            dados,
            ensure_ascii=False
        )

        return base64.urlsafe_b64encode(
            texto.encode()
        ).decode()

    @staticmethod
    def ler_token(token):

        texto = base64.urlsafe_b64decode(
            token.encode()
        ).decode()

        return json.loads(texto)