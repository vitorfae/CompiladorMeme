import sys

def rodar_interpretador(nome_arquivo):
    try:
        with open(nome_arquivo, 'r', encoding='utf-8') as f:
            linhas = f.readlines()
    except FileNotFoundError:
        print(f"o meu amor não fique triste: O arquivo '{nome_arquivo}' não foi encontrado.")
        return

    # Traduzindo a nossa linguagem de memes para Python puro
    codigo_python = []
    
    for linha in linhas:
        linha_tratada = linha.strip()

        # Ignora linhas em branco
        if not linha_tratada:
            codigo_python.append("\n")
            continue

        # entrada de dados: se é louco cachoeira -> input()
        if "se é louco cachoeira" in linha_tratada:
            linha_tratada = linha_tratada.replace("se é louco cachoeira", "input(") + ")"

        # guardando variável: aqui tem coragem -> remove a frase para virar atribuição
        if "aqui tem coragem" in linha_tratada:
            linha_tratada = linha_tratada.replace("aqui tem coragem", "").strip()

        # saída: OLHA O GÁS -> print()
        if "OLHA O GÁS" in linha_tratada:
            linha_tratada = linha_tratada.replace("OLHA O GÁS", "print(") + ")"

        # if: quero cafééé -> if ... :
        if "quero cafééé" in linha_tratada:
            condicao = linha_tratada.replace("quero cafééé", "").strip()
            linha_tratada = f"if {condicao}:"

        # else: que show da xuxa é esse -> else:
        if "que show da xuxa é esse" in linha_tratada:
            linha_tratada = "else:"

        # fechando bloco de condição: para nossa alegria -> pass
        if "para nossa alegria" in linha_tratada:
            linha_tratada = "pass"

        # laço de repetição: Irineu você não sabe nem eu -> while ...:
        if "Irineu você não sabe nem eu" in linha_tratada:
            condicao = linha_tratada.replace("Irineu você não sabe nem eu", "").strip()
            linha_tratada = f"while {condicao}:"

        # Preserva a indentação original do arquivo meme
        espacos_iniciais = len(linha) - len(linha.lstrip())
        indentacao = " " * espacos_iniciais
        
        codigo_python.append(indentacao + linha_tratada + "\n")

    # Junta todo o código traduzido
    script_para_rodar = "".join(codigo_python)

    # Bloco principal com tratamento de erro alinhado ao dicionário
    try:
        ambiente_global = {}
        exec(script_para_rodar, ambiente_global)
        print("\nsai da frente satanás")
    except Exception as e:
        print(f"\no meu amor não fique triste: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso correto: python interpretador.py seu_codigo.meme")
    else:
        rodar_interpretador(sys.argv[1])


# DICIONÁRIO
#saída: OLHA O GÁS
#if: quero cafééé
#else: que show da xuxa é esse
#problema no código: o meu amor não fique triste
#código correto: sai da frente satanás
#guardando variável: aqui tem coragem
#fechando bloco de condição: para nossa alegria
#laço de repetição: Irineu você não sabe nem eu

#entrada de dados: se é louco cachoeira 