<!-- page: relatorios -->
# Relatórios

Um relatório reúne o resultado de uma operação inteira: quem fez, quando, com que escopo, um sumário executivo para quem decide, a narrativa do trabalho para quem quer entender, as vulnerabilidades encontradas e as evidências. É o que a área responsável recebe ao fim de um pentest, entregue de uma vez, como uma unidade.

Enquanto está em rascunho, um relatório é um espaço de trabalho fechado. As vulnerabilidades dentro dele não têm vida própria: são escritas, revisadas e enviadas junto com o relatório. Só depois do envio elas passam a seguir o ciclo normal de uma vulnerabilidade, aparecem para o time de defesa e são corrigidas uma a uma.

Este capítulo mostra como criar um relatório e reservá-lo para edição, o que vai em cada parte dele e o que acontece no envio.

<!-- page: rel-criar -->
# Criar e reservar um relatório

Para começar um relatório, abra **Relatórios** no menu e escolha **Criar Relatório**. Você pode partir do zero ou escolher um **template**, que já traz o sumário executivo, a introdução e as seções adicionais com textos prontos para ajustar. O relatório copia o texto do template no momento da criação, e o capítulo [Templates](#templates) explica como eles funcionam.

## A reserva

Um relatório é um documento longo, escrito por várias pessoas, e duas delas editando ao mesmo tempo acabariam desfazendo o trabalho uma da outra. Por isso, para editar um relatório é preciso primeiro **reservá-lo**, com o botão **Editar**. Enquanto a reserva é sua, ninguém mais altera o relatório nem as vulnerabilidades dentro dele, e quem abrir o relatório verá quem está editando.

A reserva é liberada quando você sai da edição, ou sozinha, depois de **10 minutos** sem atividade, para que um relatório não fique preso só porque alguém fechou a janela. Se você precisa editar e a reserva está com outra pessoa, fale com ela; em último caso, um administrador pode liberar a reserva.

<!-- page: rel-conteudo -->
# O conteúdo de um relatório

Um relatório é organizado em partes, de cima para baixo na página, na mesma ordem em que elas aparecem no documento entregue.

As **Informações Gerais** e os **Dados do Relatório** descrevem a operação: o nome, o cliente, as datas, o tipo e o modelo do teste, o ambiente, a origem da demanda e o escopo. Em seguida vêm os textos: o **Sumário Executivo**, para quem precisa da conclusão sem os detalhes técnicos, e a **Introdução**, que situa o trabalho. Se o relatório precisa de mais texto, como uma metodologia ou uma lista de limitações, as **Seções Adicionais** permitem criar quantas forem necessárias, cada uma com o seu título e na ordem que você quiser.

Depois dos textos vêm as **vulnerabilidades** da operação, as **evidências** do relatório como um todo e as **notas internas**, que, como nas vulnerabilidades, nunca saem do portal.

Fora da edição, a página mostra o conteúdo como ele aparece no documento. Durante a edição, cada parte vira um formulário.

## As vulnerabilidades do relatório

Durante a edição, a parte *Vulnerabilidades* tem três ações. **Adicionar vulnerabilidade** cria uma nova, já dentro do relatório. **Vincular** traz para o relatório vulnerabilidades avulsas que ainda não foram enviadas: uma vulnerabilidade *Pronta* volta a *Rascunho* ao entrar, mantendo o seu ID interno, e passa a ser editada e enviada com o relatório. **Desvincular** faz o caminho inverso: a vulnerabilidade sai do relatório e volta a ser avulsa, em rascunho.

## O que vai para o documento

Nem tudo o que está no portal precisa ir para o documento. Ao lado do título de cada seção há a opção **No documento**, que diz se ela entra nos arquivos gerados: o **Exportar** (PDF, Word e Excel), a exportação em lote e o relatório enviado. Uma seção desmarcada continua no portal, mas fica de fora dos documentos; no Excel, a célula correspondente fica vazia.

A opção existe nos Dados do Relatório, no Sumário Executivo, na Introdução e em cada seção adicional, e também, nas vulnerabilidades, na Descrição, nos Detalhes do Achado, na Mitigação / Solução e nas Referências. A escolha é salva na hora, sem precisar reservar nem salvar o relatório, e pode ser mudada a qualquer momento, inclusive depois do envio, por quem pode alterar o registro. As notas internas, essas, nunca entram em documento algum.

<!-- page: rel-envio -->
# Envio, progresso e exclusão

Um relatório tem só dois status: **Rascunho**, enquanto está sendo escrito, e **Enviado**. O envio é o momento em que tudo se fecha de uma vez. **Enviar** dá ao relatório o seu ID interno (`OP-xxxx`), atribui IDs internos às vulnerabilidades que ainda não os têm, gera os documentos e os entrega. As vulnerabilidades passam a *Enviadas* e, dali em diante, seguem o ciclo normal, cada uma no seu ritmo.

## Quando o envio falha

O envio acontece em duas etapas: primeiro o portal congela o relatório, depois gera e entrega os documentos. Se a entrega falhar, por exemplo porque o servidor de e-mail não respondeu, o relatório não fica pela metade. Ele continua em *Rascunho*, bloqueado para edição, com o aviso **Falha no envio**, e o botão **Tentar novamente** repete a entrega com o mesmo conteúdo.

## O progresso

Depois do envio, o portal acompanha a correção das vulnerabilidades do relatório e mostra o progresso, como *2 de 5 corrigidas*. Quando todas estão corrigidas, ou com o risco assumido pelo time de defesa, o relatório aparece como **Concluído**. Ninguém precisa marcar isso: o portal calcula a partir do status de cada vulnerabilidade.

## Excluir

Só um relatório em rascunho pode ser excluído. Depois do envio, ele faz parte do histórico do que foi entregue e permanece no portal.
