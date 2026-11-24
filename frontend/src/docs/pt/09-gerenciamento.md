<!-- page: gerenciamento -->
# Administração

Este capítulo é para quem administra o portal. Ele trata do que mantém o portal funcionando para os outros: as contas das pessoas e o que cada uma alcança, as chaves dos sistemas integrados, os templates da equipe e as reservas de relatório que ficam presas. Os logs de auditoria, que os administradores também consultam, têm o seu próprio capítulo.

Como administrador, você vê e altera tudo no portal, e vê também a documentação de todos os papéis, inclusive as partes do time de defesa e dos dashboards, para saber o que cada público encontra.

<!-- page: adm-usuarios -->
# Usuários e acesso

A página **Usuários**, no menu, lista todas as contas. Você pode buscar pelo login e filtrar por papel ou por situação, e o usuário selecionado fica no endereço da página, para que você possa mandar o link a outro administrador.

Para criar uma conta, use **Novo usuário** e informe o login, uma senha temporária e o papel. Entregue a senha à pessoa por um canal seguro; no primeiro acesso, ela será obrigada a trocá-la. O papel pode ser mudado depois, na ficha do usuário, e a mudança vale imediatamente.

Quando alguém esquece a senha, **Redefinir senha** define uma nova senha temporária e obriga a troca no próximo acesso; as sessões abertas dessa pessoa ficam bloqueadas até a troca. Quando alguém sai da equipe, **Desativar** bloqueia o acesso na hora, inclusive nas sessões que estiverem abertas. Você não pode desativar a sua própria conta.

## O que cada um alcança

Nos papéis restritos, nem sempre é óbvio o que uma pessoa consegue ver. A ficha de cada usuário tem uma lista de acesso que responde a isso: ela mostra quais vulnerabilidades e relatórios a pessoa alcança e por quê. O motivo pode ser *Criou*, *Operador*, *Compartilhado*, pelo campo *Compartilhado com*, ou *Via relatório*, para as vulnerabilidades de um relatório que a pessoa acessa. Para os papéis com acesso total (Administrador, Editor e Leitor de todos, e Auditor), a ficha simplesmente diz que a pessoa vê tudo.

Vale consultar essa lista antes de compartilhar algo com um Editor ou Leitor restrito, para ter certeza de que ele verá o que deve, e só isso.

<!-- page: adm-chaves -->
# Chaves de API

Cada sistema que conversa com o portal pela API usa uma chave, e é o administrador quem as cria, na página **Chaves de API**. Crie uma chave por sistema, com um nome que diga de qual sistema ela é, apenas os escopos que ele usa e, de preferência, uma data de expiração. A seção [Chaves, escopos e autenticação](#api-chaves) descreve cada escopo.

A chave completa aparece uma única vez, logo depois da criação. Copie-a e entregue-a ao responsável pelo sistema por um canal seguro. Depois disso, o portal mostra apenas o prefixo, e não há como recuperar o resto; se uma chave se perder, crie outra.

A lista de chaves mostra os escopos, a expiração e o último uso de cada uma, o que ajuda a encontrar chaves esquecidas. **Revogar** desativa uma chave na hora: faça isso com as que não são mais usadas e com qualquer uma que possa ter vazado.

O escopo `vulns:import` pede um cuidado a mais, porque deixa a chave criar vulnerabilidades com status, datas e números do passado. Dê-o apenas à chave do script que traz vulnerabilidades antigas, e revogue essa chave quando a importação terminar.

<!-- page: adm-templates -->
# Aprovação de templates

Os templates compartilhados são da equipe toda, e por isso passam por um administrador antes de aparecer para todos. Na página **Templates**, o atalho **N aguardando aprovação** lista os pedidos de compartilhamento. Abra cada template e leia o conteúdo antes de decidir.

**Aprovar** deixa o template *Compartilhado*, disponível para todos. **Recusar** o devolve a *Privado*, para que o autor o ajuste e peça de novo, se quiser. Mais tarde, se um template compartilhado deixar de servir, **Remover compartilhamento** o deixa *Indisponível* para todos, inclusive para o autor, e **Compartilhar novamente** o reativa.

Como administrador, você vê todos os templates, inclusive os privados, e pode editar ou excluir qualquer um.

<!-- page: adm-reservas -->
# Reservas de relatório

Enquanto alguém edita um relatório, a página do relatório mostra quem tem a reserva e desde quando. Na maior parte das vezes, não é preciso fazer nada: se a pessoa sair sem liberar a reserva, ela expira sozinha depois de 10 minutos sem atividade.

Quando não dá para esperar, **Liberar bloqueio**, na página do relatório, libera a reserva na hora. Faça isso com cuidado, porque as alterações que a pessoa ainda não tinha salvado se perdem. A liberação fica registrada nos logs de auditoria.
