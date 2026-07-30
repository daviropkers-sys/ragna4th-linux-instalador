
# Ragna4th Linux Instalador

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python\&logoColor=white)
![Linux](https://img.shields.io/badge/Platform-Linux-FCC624?logo=linux\&logoColor=black)
![License](https://img.shields.io/badge/License-MIT-green)

Instalador e atualizador comunitário do Ragna4th para Linux.

> Este é um projeto independente e não possui afiliação oficial com a equipe do Ragna4th. Nenhum arquivo do jogo é distribuído neste repositório.

## Sobre o projeto

O launcher oficial do Ragna4th utiliza Microsoft Edge WebView2, que pode apresentar uma tela branca ou preta quando executado pelo Wine.

Este projeto oferece uma alternativa nativa em Python que consulta o manifesto oficial do Ragna4th, baixa os arquivos diretamente da infraestrutura do jogo e verifica a integridade de cada download.

## Recursos

* Baixa os arquivos diretamente do servidor oficial;
* Verifica a integridade do manifesto;
* Confere o tamanho e o SHA-256 de cada arquivo;
* Ignora arquivos que já estão completos e corretos;
* Permite atualizar uma instalação existente;
* Bloqueia caminhos potencialmente perigosos;
* Mostra velocidade e progresso dos downloads;
* Não precisa de `sudo`;
* Utiliza somente a biblioteca padrão do Python.

## Requisitos

* Linux;
* Python 3.10 ou mais recente;
* Aproximadamente 9 GB de espaço livre;
* Wine, Proton ou Lutris para executar o jogo depois da instalação.

O instalador em si não depende do Wine. O Wine ou Lutris é necessário somente para executar os arquivos do jogo.

## Instalação

Baixe o arquivo `instalar_ragna4th.py` deste repositório.

Abra o terminal na pasta em que o arquivo foi salvo e execute:

```bash
python3 instalar_ragna4th.py
```

Não use `sudo`.

O programa consultará o servidor oficial, verificará os arquivos existentes e mostrará quanto precisa ser baixado.

Quando aparecer:

```text
Iniciar o download agora? [s/N]
```

Digite:

```text
s
```

Por padrão, o cliente será instalado em:

```text
~/Games/Ragna4th
```

## Opções disponíveis

### Somente verificar

Para consultar o manifesto e verificar quanto falta baixar sem iniciar o download:

```bash
python3 instalar_ragna4th.py --plan
```

### Confirmar automaticamente

Para iniciar sem pedir confirmação:

```bash
python3 instalar_ragna4th.py --yes
```

### Escolher outra pasta

```bash
python3 instalar_ragna4th.py "$HOME/Jogos/Ragna4th"
```

## Atualização

Execute o mesmo instalador novamente:

```bash
python3 instalar_ragna4th.py
```

Os arquivos que já estiverem corretos serão verificados e ignorados. Somente arquivos ausentes, corrompidos ou desatualizados serão baixados novamente.

## Configuração inicial do jogo

Após o download, execute uma vez o configurador:

```text
# 1 Setup - USE ESTE.exe
```

No Lutris, utilize temporariamente este executável:

```text
/home/SEU_USUARIO/Games/Ragna4th/# 1 Setup - USE ESTE.exe
```

Configure inicialmente:

* Resolução: `1280x720`;
* Modo janela;
* Direct3D;
* Som ativado.

Depois, altere o executável no Lutris para:

```text
/home/SEU_USUARIO/Games/Ragna4th/ragna4th.exe
```

Use a própria pasta do jogo como diretório de trabalho:

```text
/home/SEU_USUARIO/Games/Ragna4th
```

## Segurança

Antes de aceitar um manifesto, o instalador verifica seu digest SHA-256.

Cada arquivo baixado também é validado individualmente usando:

* Nome hash fornecido pelo servidor;
* Tamanho esperado;
* SHA-256 completo;
* Caminho de destino seguro.

O arquivo só substitui a versão anterior depois que todas as verificações são concluídas.

## Arquivos que não devem ser enviados ao GitHub

Este repositório deve conter somente o código e sua documentação.

Não envie:

```text
*.exe
*.dll
*.grf
*.4th
*.mp3
```

Os arquivos do jogo pertencem aos seus respectivos responsáveis e são obtidos diretamente da infraestrutura oficial.

## Limitações

* A compatibilidade do jogo com Wine ou Proton não é garantida;
* Sistemas anticheat podem apresentar limitações no Linux;
* Mudanças futuras na infraestrutura oficial podem exigir atualizações neste instalador;
* Este projeto não oferece suporte oficial ao Ragna4th.

## Aviso legal

Ragna4th, Ragnarok Online e marcas relacionadas pertencem aos seus respectivos proprietários.

Este projeto não modifica, hospeda ou redistribui arquivos do jogo. Ele apenas automatiza o processo de download usando informações publicadas pelo atualizador oficial.

## Licença

O código deste instalador está disponível sob a licença MIT.

A licença cobre somente o código presente neste repositório. Ela não cobre o Ragna4th, Ragnarok Online ou quaisquer arquivos baixados pelo instalador.

## Créditos

Desenvolvido por Davi R. Santos
