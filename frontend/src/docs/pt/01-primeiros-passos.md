<!-- page: primeiros-passos -->
# Primeiros passos

Antes de registrar a primeira vulnerabilidade, vale conhecer o terreno: como entrar, como o portal está organizado, quanto tempo uma sessão dura e o que o seu papel permite fazer. Este capítulo trata desses pontos. Se você já usa o portal há algum tempo, pode passar ao capítulo seguinte e voltar aqui quando precisar.

<!-- page: inicio -->
# Entrando e se localizando

No primeiro acesso, use o login e a senha temporária que o administrador lhe passou. Antes de mostrar qualquer outra coisa, o portal pede uma senha nova, e o mesmo acontece sempre que um administrador redefine a sua senha. Escolha a nova senha no **Perfil**, que abre sozinho nesse momento, e o portal libera o resto.

Depois de entrar, a tela tem duas áreas fixas. À esquerda fica o menu, com um ícone para cada área do portal. O botão ☰ no topo abre o menu com os nomes por extenso; com o menu fechado, basta passar o mouse sobre um ícone para ver o que ele é. Algumas áreas têm mais de uma página: em **Relatórios**, por exemplo, ficam *Criar Relatório* e *Templates*, e você escolhe uma delas passando o mouse sobre o ícone.

No canto superior direito fica o botão com o seu usuário. Ele reúne o que não pertence a nenhuma área: o idioma do portal, esta documentação, o seu perfil, o tempo que resta da sessão e o botão para sair.

O menu mostra apenas o que o seu papel permite usar. Se uma área de que alguém falou não aparece para você, não é um erro: você não tem acesso a ela. A seção [Papéis e acesso](#papeis) explica o que cada papel vê.

<!-- page: sessao -->
# A sessão

Por segurança, uma sessão no portal não dura para sempre. Ela termina por um de dois motivos: **1 hora** depois do login, qualquer que seja o uso, ou antes disso, depois de **15 minutos sem atividade**. Conta como atividade mexer o mouse, digitar ou rolar a página, em qualquer aba do portal que esteja aberta.

O menu do seu usuário mostra os dois prazos lado a lado, no formato **Sessão mm:ss / mm:ss**. O primeiro é o tempo até a sessão terminar por inatividade, e o segundo, o tempo até o fim da hora. O portal também avisa antes de cada um. Dois minutos antes do fim por inatividade, aparece a pergunta *"Você ainda está aí?"*, e clicar em **Continuar conectado** recomeça a contagem. Cinco minutos antes do fim da hora, o portal pede que você salve o que estiver editando, porque esse prazo não pode ser estendido.

Se a sessão terminar enquanto você tem alterações não salvas, nada se perde de imediato. A página continua aberta e o portal pede a sua senha de novo; depois de entrar, salve normalmente. Se preferir abandonar o que estava fazendo, **Descartar e sair** encerra sem salvar.

Depois de cinco tentativas de login sem sucesso em 15 minutos, a conta fica bloqueada por alguns minutos. Se você esqueceu a senha, peça a um administrador que a redefina.

<!-- page: perfil -->
# Seu perfil e seu nome

O **Perfil**, no menu do seu usuário, mostra quem você é para o portal: o seu login, o seu papel e os nomes pelos quais os outros o conhecem. É também onde você troca a sua senha.

O **login** é o que você digita para entrar. Pode ser um e-mail, uma matrícula ou qualquer outro identificador que a sua organização use. Só um administrador o define, e ele não muda depois.

Além do login, você tem dois nomes, e cada um aparece num lugar diferente. O **nome completo** vai para os documentos que saem do portal, como a lista de operadores no PDF de um relatório, e por isso deve ser o seu nome formal. O **nome de exibição** é como os colegas o veem dentro do portal: na lista de operadores de uma vulnerabilidade, no aviso de quem está editando um relatório, como dono de um template. Se o nome de exibição ficar vazio, o portal usa o nome completo; se os dois estiverem vazios, usa o login.

Para mudar um nome, edite o campo e clique em **Salvar**. Deixar um campo em branco e salvar apaga aquele nome. Na busca e nos filtros, como `operator:`, tanto o nome quanto o login encontram você.

<!-- page: papeis -->
# Papéis e acesso

Cada pessoa no portal tem um **papel**, definido por um administrador, e é o papel que decide o que ela vê e o que pode alterar. A maior parte da equipe trabalha com acesso a tudo. Os papéis restritos existem para quem deve ver apenas uma parte do trabalho, e dois papéis servem a públicos de fora do Red Team.

| Papel | O que vê | O que pode fazer |
|---|---|---|
| **Administrador** | Tudo | Tudo, inclusive gerenciar usuários, chaves de API e o compartilhamento de templates |
| **Editor (todos)** | Tudo | Criar e alterar qualquer vulnerabilidade ou relatório |
| **Leitor (todos)** | Tudo | Apenas consultar |
| **Auditor** | Tudo, e também os logs de auditoria | Apenas consultar |
| **Editor restrito** | O que criou, aquilo de que é operador e o que foi compartilhado com ele | Criar vulnerabilidades e relatórios, alterar o que criou ou de que é operador, excluir só o que criou |
| **Leitor restrito** | O que criou, aquilo de que é operador e o que foi compartilhado com ele | Apenas consultar |
| **Dashboards** | Apenas contagens, nunca as vulnerabilidades | Montar dashboards e links de TV |
| **Defesa** | Apenas as vulnerabilidades enviadas, sem notas internas, operadores ou relatórios | Aceitar cada uma, registrar o RVS ou assumir o risco |

Os papéis restritos dependem de dois campos de cada registro. **Operadores** são as pessoas que trabalham no achado ou na operação. **Compartilhado com** é uma lista de quem pode acompanhar o registro sem trabalhar nele. Para que um Leitor restrito veja uma vulnerabilidade, por exemplo, basta adicioná-lo em *Compartilhado com*. As vulnerabilidades de um relatório seguem o acesso do relatório: quem vê o relatório vê todas elas.

As contas de Defesa e de Dashboards são diferentes das outras. Elas não entram nas áreas do Red Team, e cada uma tem a sua própria parte deste guia, que só ela e os administradores veem.
