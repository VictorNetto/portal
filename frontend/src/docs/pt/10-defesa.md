<!-- page: defesa -->
# O time de defesa no portal

O Red Team encontra vulnerabilidades, e o time de defesa decide o que fazer com elas. O portal é onde essas duas pontas se encontram. Cada vulnerabilidade que o Red Team envia chega até você, e para cada uma você diz o que vai acontecer. Ou ela será corrigida, e então você a **aceita** e registra o **RVS** aberto para a correção, ou ela não será, e você **assume o risco**, explicando por quê. A partir daí, o portal acompanha a correção até que o reteste confirme que o problema acabou.

## Entrando

No primeiro acesso, use a senha temporária que o administrador do portal lhe passou; o portal pede uma senha nova antes de continuar. Depois de entrar, o menu à esquerda tem uma seção para cada etapa do trabalho, explicadas em [As seções e as vulnerabilidades](#def-secoes). O botão ☰ no topo mostra os nomes das seções; com o menu fechado, passe o mouse sobre um ícone. No canto superior direito, o botão com o seu usuário reúne o idioma, esta documentação, o seu perfil, o tempo da sessão e o botão para sair.

## O que você vê

Você vê apenas as vulnerabilidades que o Red Team já enviou. Os rascunhos, as notas internas do Red Team, os nomes dos operadores e o conteúdo dos relatórios ficam de fora: o que chega até você é o que foi entregue, com as evidências.

## Confidencialidade e registro

As vulnerabilidades e as evidências são **confidenciais**. Não as copie para canais fora dos sistemas autorizados da organização.

O portal guarda um registro de quem fez o quê e quando: logins, vulnerabilidades e anexos abertos, aceitações, RVS registrados, retestes solicitados, vulnerabilidades marcadas como corrigidas, riscos assumidos e desfeitos. O Red Team e os auditores consultam esse registro.

<!-- page: def-sessao -->
# A sessão

Uma sessão no portal termina por um de dois motivos: **1 hora** depois do login, ou antes disso, depois de **15 minutos sem atividade**. O menu do seu usuário mostra os dois prazos, em **Sessão mm:ss / mm:ss**. Dois minutos antes do fim por inatividade, o portal pergunta *"Você ainda está aí?"*, e **Continuar conectado** recomeça a contagem.

Depois de cinco tentativas de login sem sucesso em 15 minutos, a conta fica bloqueada por alguns minutos. Se você esqueceu a senha, peça ao administrador do portal que a redefina.

<!-- page: def-secoes -->
# As seções e as vulnerabilidades

Cada vulnerabilidade está numa seção do menu, conforme a etapa em que se encontra, e cada seção corresponde a uma decisão que espera por você, ou a nenhuma.

**Novas** reúne as vulnerabilidades que o Red Team enviou e que ninguém do time de defesa aceitou ainda. É por ali que o trabalho começa: para cada uma, você decide entre **aceitar** e **assumir o risco**. As aceitas passam para **Aguardando RVS**, onde esperam até que você registre o RVS da correção, ou assuma o risco, se mudar de ideia. Com o RVS registrado, a vulnerabilidade vai para **Em andamento**, onde fica enquanto é corrigida e retestada; ali, quando a correção estiver pronta, você pede o reteste ou a marca como corrigida. As que o reteste confirmou ficam em **Corrigidas**, apenas para consulta. E as que o time de defesa decidiu não corrigir ficam em **Risco assumido**, de onde a decisão pode ser desfeita.

As listas mostram, para cada vulnerabilidade, o identificador, a situação, o CVSS (em vermelho a partir de 7, em laranja de 4 a 6,9), o relatório de origem, quando ela foi recebida e o ID do RVS, com cinquenta vulnerabilidades por página. Clique numa linha para abrir a vulnerabilidade.

## A página de uma vulnerabilidade

No topo da página ficam o título, a situação e o **ID interno**, como `VULN-0042`, que identifica a vulnerabilidade em qualquer conversa com o Red Team. Logo abaixo, a **linha do tempo** mostra quando ela foi recebida e cada etapa seguinte, com o ID do RVS ou a justificativa do risco assumido. Depois vêm as informações gerais (CWE, CVSS, vetor CVSS e o relatório de origem), a **Descrição**, os **Detalhes do achado** e a **Mitigação / Solução**, com as imagens de evidência no próprio texto, e por fim as **Referências** e os **Anexos**, que você salva com **Baixar**.

Os botões de ação ficam no canto superior direito e mudam conforme a etapa. O caminho no topo, como *Novas › título*, volta para a seção de onde você abriu a vulnerabilidade.

<!-- page: def-aceitar -->
# Aceitar e registrar o RVS

Começar a correção de uma vulnerabilidade leva dois passos, e eles são separados de propósito: aceitar diz ao Red Team que a vulnerabilidade foi recebida e será tratada, mesmo antes de existir um chamado para ela.

Em **Novas**, abra a vulnerabilidade e clique em **Aceitar**. Ela passa para *Aguardando RVS*, com o seu nome e a data da aceitação. Depois, abra o RVS no sistema da sua área e, na vulnerabilidade, informe o **ID do RVS** e clique em **Registrar RVS**. Ela passa para *Em andamento*, e a correção começa. É preciso aceitar antes de registrar o RVS.

## O ID do RVS

Cada vulnerabilidade tem o seu próprio RVS. Um ID que já foi usado em outra vulnerabilidade é recusado, e a mensagem diz qual vulnerabilidade o tem. Maiúsculas e espaços não contam na comparação: `RVS-1` e ` rvs-1 ` são o mesmo ID.

O ID não pode ser alterado depois de registrado. Se você registrou um ID errado, peça ao Red Team que o corrija: um administrador devolve a vulnerabilidade a *Aguardando RVS*, e você registra o ID certo.

<!-- page: def-risco -->
# Assumir o risco

Nem toda vulnerabilidade será corrigida. O sistema pode estar perto de ser desativado, pode haver um controle que compensa a falha, ou a área de negócio pode decidir conviver com ela. Nesses casos, em vez de aceitar, use **Assumir risco**, em *Novas* ou em *Aguardando RVS*.

O portal pede uma justificativa, de pelo menos cinco caracteres, e ela é obrigatória: é o registro de por que aquela falha continua existindo, e o Red Team a vê na linha do tempo. A vulnerabilidade vai para **Risco assumido**, e o caminho dela termina ali, como se tivesse sido corrigida. Um relatório é considerado concluído quando todas as suas vulnerabilidades estão corrigidas ou com o risco assumido.

Se a decisão mudar, abra a vulnerabilidade em *Risco assumido* e use **Desfazer risco assumido**. Ela volta para *Novas*, ou para *Aguardando RVS*, se já tinha sido aceita. A justificativa anterior não se perde: fica guardada no registro de auditoria.

<!-- page: def-lote -->
# Várias vulnerabilidades de uma vez

Um relatório costuma trazer muitas vulnerabilidades, e tratá-las uma a uma seria lento. Nas seções com ações (*Novas*, *Aguardando RVS*, *Em andamento* e *Risco assumido*), você pode agir sobre várias de uma vez.

Para escolher as vulnerabilidades, marque as caixas à esquerda das linhas; a caixa do cabeçalho marca a página inteira. Há também um atalho para o caso mais comum: clicar no nome de um relatório seleciona todas as vulnerabilidades dele na seção, em todas as páginas e dentro do filtro atual, e um segundo clique desfaz a seleção. Com a seleção feita, clique em **Ações** e escolha; o menu mostra apenas o que a seção permite.

A maioria das ações pede só uma confirmação: **Aceitar**, **Solicitar reteste**, **Marcar como corrigida** e **Desfazer risco assumido**. Solicitar reteste e marcar como corrigida valem apenas para as vulnerabilidades em correção; as que estão em reteste são ignoradas. **Assumir risco** pede uma justificativa, que vale para todas as selecionadas.

**Registrar RVS** é diferente, porque cada vulnerabilidade tem o seu ID. A ação abre um formulário com uma linha por vulnerabilidade, com o ID interno, o título e um campo para o RVS. Preencha o que já tiver; campos em branco ficam para depois. IDs repetidos no formulário, ou já usados em outra vulnerabilidade, são apontados na própria linha, e as linhas registradas saem do formulário, para que você veja o que falta.

Ao final de qualquer ação, o portal diz quantas vulnerabilidades foram tratadas, quantas foram ignoradas porque a ação não se aplicava a elas e quantas falharam, com o motivo de cada falha.

<!-- page: def-filtros -->
# Filtros

Cada seção tem, no topo, a caixa **Filtrar**. O texto livre procura no identificador da vulnerabilidade; para filtrar por outra coisa, escreva uma chave, dois-pontos e um valor. Digite `/` para ver as chaves disponíveis.

| Filtro | O que mostra |
|---|---|
| `status:fixing` | A situação exata: `sent`, `fixing`, `retesting`, `fixed` ou `risk_accepted` |
| `cvss:7` | As com CVSS maior ou igual a 7 |
| `report:Data` | As de um relatório cujo nome contém o texto; `report:none`, as que não vieram de um relatório |

Vários termos se combinam, e todos precisam valer ao mesmo tempo. Um `-` antes da chave exclui o que corresponde. O valor vai até o primeiro espaço, então, para valores com espaços, use aspas: `report:"Rede do Data Center"`. Cada seção começa sem filtro.

## Datas

Em **Mais filtros…**, no fim do menu do `/`, ficam os filtros por data: `sent` (recebida), `accepted` (aceita), `fixing` (início da correção), `retesting` (reteste solicitado), `fixed` (corrigida) e `risk` (risco assumido). O valor diz o período.

`sent:7d` quer dizer nos últimos sete dias, contando hoje, e da mesma forma `m` conta meses e `y` conta anos. Uma data sozinha quer dizer o período inteiro: `fixed:10-2026` é outubro de 2026, e uma data também pode ser um dia (`05-10-2026`), um ano (`2026`), um semestre (`26S1`) ou um trimestre (`26T3`). Dois pontos fazem um intervalo, com os dois lados incluídos, como `fixed:01-09-2026..30-09-2026`, e um lado vazio o deixa aberto, como `sent:01-10-2026..`.

Um `-` inverte o período: `-sent:15d` mostra as recebidas há mais de quinze dias, um bom filtro para a seção *Novas*.

<!-- page: def-depois -->
# Depois do RVS

Com o RVS registrado, a vulnerabilidade fica em **Em andamento** enquanto é corrigida. A área responsável trabalha na correção e, quando ela estiver pronta, você abre a vulnerabilidade e escolhe um de dois caminhos.

O caminho normal é **Solicitar reteste**, para que o Red Team verifique se a correção funciona. Se o reteste for aprovado, o Red Team move a vulnerabilidade para *Corrigidas*. Se não, ela volta para *Em correção*, e você pede um novo reteste quando a área corrigir de novo.

Quando o reteste não é necessário, **Marcar como corrigida** leva a vulnerabilidade direto para *Corrigidas*, sem a verificação do Red Team. Essa escolha fica registrada.

A linha do tempo de cada vulnerabilidade mostra quando cada etapa aconteceu.
