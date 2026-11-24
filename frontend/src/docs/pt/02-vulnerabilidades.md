<!-- page: vulnerabilidades -->
# Vulnerabilidades

Uma vulnerabilidade é o registro de um achado: uma falha encontrada num sistema, com a descrição do problema, os detalhes de como ela foi encontrada, a forma de corrigi-la e as evidências. É a unidade básica do portal. Ela pode existir sozinha, como um achado avulso, ou dentro de um relatório, junto com as outras vulnerabilidades de uma operação.

Uma vulnerabilidade passa por várias etapas, do rascunho que você começa a escrever até a correção confirmada pelo reteste, e o portal guarda a data de cada uma. Este capítulo segue esse caminho: como criar e escrever uma vulnerabilidade, por quais status ela passa, o que acontece depois que ela é enviada e como o portal lida com duas pessoas editando a mesma vulnerabilidade.

## As três identificações de um registro

Antes de começar, vale conhecer as três identificações que aparecem nas telas, porque elas surgem em momentos diferentes.

O **identificador** é o nome que você dá ao achado, como *SQL injection no Portal do Cliente*. É ele que aparece nas listas e nos títulos, e você pode mudá-lo enquanto o conteúdo estiver aberto para edição.

O **ID interno** é o número que o portal atribui, como `VULN-0012`, ou `OP-0003` no caso de um relatório. Uma vulnerabilidade avulsa o recebe quando é concluída; um relatório e as vulnerabilidades dentro dele, quando o relatório é enviado. Antes disso o registro não tem número, e depois o número nunca muda. É o ID interno que identifica o achado em qualquer conversa com outras áreas.

O **RVS** é o número dado pelo time de defesa quando ele aceita corrigir a vulnerabilidade. Só existe em vulnerabilidades, só depois do envio, e também não muda depois de registrado.

<!-- page: vuln-criar -->
# Criar uma vulnerabilidade

Para registrar um achado, abra o menu e escolha **Criar Vulnerabilidade**. O formulário que aparece é o mesmo que você usará depois para editá-la, e nada precisa estar completo agora: você pode salvar um rascunho só com o identificador e voltar a ele quantas vezes quiser. Apenas para **concluir** a vulnerabilidade é que três campos passam a ser obrigatórios: o **Identificador**, a **Descrição** e os **Detalhes do Achado**. A **Mitigação / Solução** pode ficar em branco, para os casos em que a correção cabe a quem conhece o sistema.

## Quem trabalha no achado

Você começa como operador da vulnerabilidade. Se outras pessoas trabalharam no achado, adicione-as com o botão **+** ao lado de **Operadores**; para remover alguém, clique no nome. Logo ao lado, **Compartilhado com** funciona do mesmo jeito, mas para quem deve apenas acompanhar o registro, como um Leitor restrito que precisa ver aquele achado.

## A nota CVSS

A severidade segue a CVSS v3.1. Se você já tem a nota e o vetor, digite-os nos campos. Se não, clique em **Calculadora**, ao lado do campo *Vetor CVSS*. Ela mostra as oito métricas base (vetor de ataque, complexidade, privilégios, interação do usuário, escopo e os três impactos) e calcula a nota, a severidade e o vetor exatamente como a calculadora oficial da FIRST. **Aplicar** preenche os dois campos. Se a vulnerabilidade já tiver um vetor, a calculadora abre com ele, o que facilita ajustar uma métrica sem refazer as outras.

## A data de criação

A **Data de criação** começa com o dia de hoje, e quase sempre é isso mesmo. Às vezes, porém, um achado é registrado dias depois de encontrado, e nesse caso vale corrigir a data, porque a linha do tempo da vulnerabilidade e as durações dos dashboards contam a partir dela. Datas no futuro não são aceitas. A data só pode ser mudada enquanto o conteúdo estiver aberto para edição, isto é, em rascunho ou pronta, e mesmo então não pode ficar depois do dia em que a vulnerabilidade foi concluída.

## O que pode aparecer no topo

Ao lado do status, no topo da página, duas anotações podem aparecer. **Lote `BATCH-0001`** indica que a vulnerabilidade faz parte de um lote, em geral criado por uma ferramenta que registrou vários achados de uma vez pela API. Clicar no lote mostra, nas Operações, todas as vulnerabilidades que vieram com ela. **Importada em …** indica que ela veio de outro sistema já com o seu histórico (status, datas, número e RVS), e que as datas da linha do tempo são as de lá, não de trabalho feito no portal.

<!-- page: textos -->
# Textos, imagens e anexos

Os campos de texto longos, como a Descrição e os Detalhes do Achado, usam **Markdown**, uma forma simples de formatar texto com alguns símbolos: `**negrito**`, `*itálico*`, `# título`, listas começando com `-`, e assim por diante. Você não precisa decorar nada disso, porque a barra do editor tem botões para negrito, itálico, título, listas, código, link e citação. **Visualizar** mostra o texto como ele vai aparecer.

Quando você precisa de espaço, **Expandir** deixa o editor da altura da janela; **Recolher**, ou a tecla *Esc*, o devolve ao tamanho normal.

## Imagens

Uma captura de tela costuma ser a melhor evidência, e por isso o editor aceita imagens diretamente: cole uma imagem, arraste um arquivo para o texto ou escolha um pelo botão de imagem. O portal pede um nome para ela, guarda o arquivo como evidência e insere a imagem no ponto do texto em que você estava. Nos documentos exportados, ela aparece no mesmo lugar.

## Anexos

Para evidências que não cabem no texto, como um log ou um arquivo de requisições, use a área de **Anexos**. Cada arquivo pode ter até 50 MB, nos formatos PDF, PNG, JPG, GIF, WebP, TXT, CSV e ZIP. O portal confere o tipo pelo conteúdo do arquivo, e não só pela extensão; um executável renomeado para `.png` é recusado.

## Notas internas

O campo **Notas internas** é para o que interessa só à equipe: hipóteses, pendências, o contexto da operação. Ele nunca sai do portal, nem nas exportações, nem nos relatórios entregues, nem pela API. Por isso, junto com os operadores, é o que continua editável depois do envio.

<!-- page: vuln-ciclo -->
# O ciclo de vida

Toda vulnerabilidade está num **status**, que diz em que ponto do caminho ela está e quem deve agir em seguida. O caminho normal tem seis etapas, quase sempre percorridas em ordem.

Uma vulnerabilidade nasce como **Rascunho**. Nessa fase, ela pode ser salva quantas vezes for preciso com **Salvar rascunho**, mesmo incompleta. Quando o achado estiver descrito, **Concluir** confere os campos obrigatórios e atribui o ID interno `VULN-xxxx`, e a vulnerabilidade passa a **Pronta**.

Uma vulnerabilidade **Pronta** está completa, mas ainda não saiu do Red Team. Ela continua editável, para uma revisão final. Quando tudo estiver certo, **Enviar** a entrega à área responsável.

Ao ser enviada, a vulnerabilidade fica **Enviada** e o seu conteúdo se fecha para edição: o que foi entregue não muda mais. Agora é a vez do time de defesa, que tem dois caminhos. O mais comum é **aceitar** a vulnerabilidade e registrar o ID de RVS aberto para corrigi-la, o que a leva para **Em correção**. O outro é **assumir o risco** de não corrigir, com uma justificativa, o que encerra o caminho com o status **Risco assumido**. A justificativa aparece na linha do tempo, e a defesa pode desfazer essa decisão depois, devolvendo a vulnerabilidade a *Enviada*.

**Em correção**, a área responsável trabalha no problema. Quando termina, o time de defesa pede a verificação com **Solicitar reteste**; o Red Team também pode fazer esse pedido. Se o reteste não for necessário, a defesa pode usar **Marcar como corrigida**, que leva a vulnerabilidade direto ao fim.

**Em reteste**, o Red Team verifica se a correção funciona. Se funciona, **Aprovar reteste** leva a vulnerabilidade a **Corrigida**, o fim do caminho. Se não, **Reprovar reteste** a devolve para *Em correção*, e o ciclo se repete até a correção passar.

A linha do tempo, no topo da página de cada vulnerabilidade, mostra quando cada uma dessas etapas aconteceu.

<!-- page: vuln-apos -->
# Depois do envio: o RVS e os ajustes

O envio é um ponto sem volta para o conteúdo. A partir dele, o que foi entregue fica como foi entregue, e só os **operadores** e as **notas internas** continuam editáveis, porque dizem respeito ao trabalho da equipe, e não ao que a outra área recebeu.

## O RVS

O RVS é o número com que o time de defesa acompanha a correção nos seus próprios sistemas. Quem o registra é o próprio time de defesa, com uma conta de papel Defesa no portal: ele aceita a vulnerabilidade enviada e informa o ID, e a vulnerabilidade passa para *Em correção*. Cada ID pertence a uma única vulnerabilidade e não muda depois de registrado.

Do lado do Red Team, não é preciso fazer nada para isso acontecer, mas dá para acompanhar. A linha do tempo de cada vulnerabilidade mostra o RVS assim que ele é registrado, ou a justificativa, se a defesa assumiu o risco. Para ver tudo o que ainda espera resposta da defesa, filtre as Operações por `status:sent`; `status:sent -sent:15d` mostra as que esperam há mais de quinze dias.

## Quando algo sai errado

Às vezes um status muda por engano, ou um RVS é registrado na vulnerabilidade errada. Nesses casos, um administrador pode usar **Ajustar status** para devolver a vulnerabilidade a uma etapa anterior, informando o motivo, e o ajuste fica registrado nos logs de auditoria. No caso de um RVS errado, o administrador devolve a vulnerabilidade a *Enviada*, e a defesa registra o ID certo.

<!-- page: vuln-conflitos -->
# Edições simultâneas

Numa equipe, é natural que duas pessoas abram a mesma vulnerabilidade ao mesmo tempo. O portal não impede isso, mas impede que uma apague o trabalho da outra sem perceber.

Cada vulnerabilidade guarda uma versão, que aumenta a cada alteração salva. Quando você salva, o portal confere se a versão que você abriu ainda é a atual. Se alguém salvou nesse meio-tempo, o seu salvamento é recusado com um aviso, e a página mostra a versão mais recente. Nada do que a outra pessoa escreveu é sobrescrito: você confere o que mudou e refaz a sua alteração sobre a versão nova.

O mesmo vale para mudanças que chegam de fora. Se uma ferramenta altera a vulnerabilidade pela API enquanto você a edita, você verá o aviso ao salvar.

Os relatórios funcionam de outro jeito, com uma reserva que impede a edição simultânea desde o começo. O próximo capítulo explica como.
