<!-- page: auditoria -->
# Logs de auditoria

O portal registra quase tudo o que acontece nele: logins, criações, alterações, mudanças de status, envios, exportações, leituras de anexos e liberações de reserva. Cada entrada diz quem agiu (uma pessoa, uma chave de API, que aparece como `api:<prefixo>`, ou o próprio sistema), quando, de qual endereço IP e o que exatamente mudou. É esse registro que permite responder, meses depois, quem enviou um relatório, quem abriu uma evidência ou por que um status mudou.

Os logs ficam no menu, em **Logs de Auditoria**, e só administradores e auditores os veem. A página é uma lista, da entrada mais recente para a mais antiga. Clicar numa linha mostra o detalhe completo da entrada e um atalho para abrir o registro de que ela trata.

<!-- page: auditoria-filtros -->
# Filtrando os logs

A caixa de filtro dos logs funciona como a das Operações: texto livre e filtros com chave, que se combinam, e `/` para ver a lista de chaves. A diferença é que, aqui, o texto livre procura em tudo: no autor, na ação, no registro, no detalhe e no IP.

| Filtro | O que mostra |
|---|---|
| `action:update,delete` | As entradas de uma dessas ações |
| `actor:maria` | O que uma pessoa fez, pelo login, pelo nome de exibição ou pelo nome completo |
| `actor:api:<prefixo>` | O que uma chave de API fez; `actor:system`, o que o próprio portal fez |
| `entity:report` | As entradas sobre um tipo de registro; `entity:none`, as que não tratam de registro algum |
| `record:VULN-0012` | Tudo sobre um registro, pelo ID interno ou pelo UUID, incluindo os seus anexos |
| `date:7d` | Quando aconteceu, com os mesmos períodos das Operações, como `date:10-2026` |

Em **Mais filtros…** ficam `role:admin`, o papel de quem agiu, `ip:10.0.`, o endereço de origem, e `detail:password`, que procura no detalhe da entrada.

Como nas Operações, um `-` antes da chave exclui o que corresponde, e aspas permitem valores com espaços. Há também um atalho: clicar num valor da lista, como um autor, uma ação, um tipo, um registro ou um IP, filtra por ele.

A busca fica guardada no endereço da página. Para mostrar a alguém exatamente o que você está vendo, copie o link.
