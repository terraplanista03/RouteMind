class RouteFormatter:

    def formatar(self, rotas, entregas):

        resultado = []

        for numero_motorista, rota in enumerate(rotas):

            roteiro = []

            for indice in rota:

                if indice == 0:

                    roteiro.append({

                        "tipo": "Origem",

                        "endereco": "Origem"

                    })

                    continue

                entrega = entregas[indice - 1]

                roteiro.append({

                    "tipo": "Entrega",

                    "endereco": entrega.endereco,

                    "cidade": entrega.cidade,

                    "bairro": entrega.bairro,

                    "latitude": entrega.latitude,

                    "longitude": entrega.longitude

                })

            resultado.append({

                "motorista": numero_motorista + 1,

                "quantidade_entregas": len(roteiro) - 2,

                "roteiro": roteiro

            })

        return resultado