<!-- page: operacoes -->
# Operações: encontrar e exportar

Com o tempo, o portal acumula centenas de vulnerabilidades e dezenas de relatórios. A página **Operações** é onde você os encontra. Ela tem duas abas, uma para vulnerabilidades e outra para relatórios, e cada aba é uma lista com uma linha por registro.

A lista mostra só o essencial. Clicar numa linha abre, logo abaixo da lista, o painel de detalhes, com todas as informações e a linha do tempo; o botão **Abrir** leva à página do registro. Para agir sobre vários registros de uma vez, marque as linhas nas caixas à esquerda e use o menu **Ações**, que permite exportar, enviar ou excluir. Registros que não podem receber a ação escolhida, como um relatório já enviado numa exclusão, são ignorados, e o portal diz quais foram.

Este capítulo mostra como filtrar a lista para encontrar o que você procura, inclusive por datas, e como tirar documentos do portal.

<!-- page: filtros -->
# Filtrando a lista

A caixa **Filtrar**, no topo da lista, aceita texto livre e filtros com chave. O texto livre procura no identificador: digitar `sql` mostra as vulnerabilidades com "sql" no nome. Para filtrar por outra coisa, escreva uma chave, dois-pontos e um valor, como `status:draft`. Não é preciso lembrar das chaves: digite `/` e o portal mostra a lista.

| Filtro | O que mostra |
|---|---|
| `status:draft` | As vulnerabilidades naquele status; `status:sent,fixing` aceita mais de um |
| `cvss:7` | As com CVSS maior ou igual a 7 |
| `report:nome` | As de um relatório cujo nome contém o texto; `report:none`, as que não estão em relatório |
| `operator:nome` | As que têm aquela pessoa como operadora, pelo nome ou pelo login |
| `batch:BATCH-0001` | As que vieram naquele lote pela API; `batch:none`, as que não vieram em lote |

Os termos se combinam, e todos precisam valer ao mesmo tempo: `status:sent cvss:7` mostra as enviadas com CVSS 7 ou mais. Um `-` antes da chave inverte o filtro, e `-status:fixed` mostra tudo o que não está corrigido.

O valor de um filtro vai até o primeiro espaço. Se ele tem espaços, como o nome de um relatório, use aspas: `report:"Rede do Data Center"`.

No fim do menu do `/`, **Mais filtros…** mostra os filtros menos usados, como `source:nuclei`, que procura na fonte do achado, e os filtros por data, que têm uma página só para eles.

<!-- page: filtros-datas -->
# Filtrando por datas

Uma vulnerabilidade acumula datas ao longo do caminho: quando foi criada, enviada, aceita, corrigida. Os filtros de data usam qualquer uma delas e respondem a perguntas como "o que foi corrigido em setembro?" ou "o que foi enviado há mais de quinze dias e continua sem resposta?".

Um filtro de data tem uma chave, que diz qual data olhar, e um valor, que diz o período.

| Chave | A data |
|---|---|
| `created` | Criação |
| `updated` | Última alteração |
| `sent` | Envio |
| `accepted` | Aceitação pelo time de defesa |
| `fixing` | Início da correção |
| `retesting` | Pedido de reteste |
| `fixed` | Correção confirmada |
| `risk` | Risco assumido |

## Períodos relativos

O jeito mais simples de dizer um período é contar para trás a partir de hoje. `created:7d` mostra o que foi criado nos últimos sete dias, contando hoje (`1d` é só hoje). Da mesma forma, `m` conta meses e `y` conta anos: `fixed:3m` é o que foi corrigido nos últimos três meses.

## Datas e intervalos

Para um período fixo, escreva datas. Uma data pode ser um dia (`05-10-2026`), um mês (`10-2026`), um ano (`2026`), um semestre (`26S1` ou `2026S1`) ou um trimestre (`26T3`, ou `26Q3`). Uma data sozinha quer dizer o período inteiro: `fixed:10-2026` é tudo o que foi corrigido em outubro de 2026.

Para um intervalo, ponha dois pontos entre o começo e o fim. `fixed:01-09-2026..30-09-2026` vai de 1º a 30 de setembro, com os dois dias incluídos, e `fixed:09-2026..10-2026` cobre setembro e outubro inteiros. Deixar um dos lados vazio abre o intervalo: `sent:01-10-2026..` é de 1º de outubro em diante, e `sent:..31-12-2025` é até o fim de 2025.

## Invertendo o período

Com um `-` na frente, o período se inverte: `-updated:30d` mostra o que *não* foi alterado nos últimos trinta dias. Há um detalhe: uma vulnerabilidade que nem tem aquela data também entra no resultado, já que ela não está dentro do período. Por isso, filtros invertidos funcionam melhor combinados com um status. Este filtro mostra as vulnerabilidades enviadas há mais de quinze dias que ainda esperam resposta do time de defesa:

```
status:sent -sent:15d
```

E este, os rascunhos esquecidos há um mês:

```
status:draft -updated:30d
```

Nos relatórios, valem `created`, `updated` e `sent`. Todas as datas seguem o fuso horário do seu navegador.

<!-- page: exportar -->
# Exportando documentos

Cedo ou tarde, o que está no portal precisa virar um arquivo: para anexar a um e-mail, para uma reunião, para arquivar. O botão **Exportar**, nas páginas de vulnerabilidade e de relatório, reúne os formatos disponíveis. Uma vulnerabilidade pode ser exportada em PDF ou Word. Um relatório pode ser exportado em PDF ou Word, e também em Excel, com a planilha das suas vulnerabilidades.

Para exportar muitos registros de uma vez, use as Operações: marque as linhas e escolha a exportação no menu **Ações**. O resultado é um ZIP com um PDF por registro, ou uma planilha Excel com todos eles.

Os documentos exportados são os mesmos que a área responsável recebe no envio, com as imagens de evidência no lugar e sem as seções marcadas como fora do documento (veja [O conteúdo de um relatório](#rel-conteudo)). As notas internas nunca vão para um arquivo exportado.
