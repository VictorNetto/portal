// User documentation shown on the Documentação page (/docs).
// Sections hold subsections; each subsection is Markdown rendered by MarkdownView.
// `roles` (on a section or a subsection) limits it to the roles that can use what
// it describes — the page hides the rest, like the nav. A section whose
// subsections are all hidden is hidden too.

const CREATORS = ['admin', 'write_all', 'write_restricted']

const pt = [
  {
    id: 'geral', title: 'Informações Gerais',
    subs: [
      {
        id: 'inicio', title: 'Primeiros passos',
        md: `O portal reúne as **vulnerabilidades** encontradas pela equipe de Red Team e os **relatórios** entregues às áreas responsáveis.

- **Menu à esquerda:** os ícones levam às áreas do portal. O botão ☰ no topo abre o menu com os nomes. Em **Relatórios** ficam *Criar Relatório* e *Templates*: passe o mouse sobre o ícone para escolher.
- **Botão com seu usuário (canto superior direito):** idioma, esta documentação, seu perfil, sair e o tempo restante da sessão.
- O menu mostra apenas o que o seu papel permite usar. Se algo não aparece, você não tem acesso a essa função.`,
      },
      {
        id: 'sessao', title: 'Sessão',
        md: `- A sessão dura no máximo **1 hora** a partir do login e termina antes após **15 minutos sem atividade** (mouse, teclado ou rolagem, em qualquer aba do portal).
- No menu do seu usuário, **Sessão mm:ss / mm:ss** mostra o tempo restante: primeiro até a inatividade, depois até o fim da sessão de 1 hora.
- **2 minutos** antes do fim por inatividade aparece *"Você ainda está aí?"*: clique em **Continuar conectado**.
- **5 minutos** antes do fim da 1 hora, o portal avisa para você salvar o que estiver editando.
- Se a sessão acabar com **alterações não salvas**, a página continua aberta e o portal pede sua senha novamente. Depois de entrar, salve normalmente. **Descartar e sair** abandona as alterações.
- No primeiro acesso, ou depois que um administrador redefinir sua senha, é obrigatório trocá-la no **Perfil** antes de continuar.`,
      },
      {
        id: 'papeis', title: 'Papéis e acesso',
        md: `Cada usuário tem um papel, definido por um administrador:

- **Administrador:** vê e altera tudo; gerencia usuários, chaves de API e o compartilhamento de templates.
- **Editor (todos):** vê e altera todas as vulnerabilidades e relatórios.
- **Leitor (todos):** vê tudo, sem alterar.
- **Auditor:** vê tudo e consulta os logs de auditoria.
- **Editor restrito:** cria vulnerabilidades e relatórios; vê e altera os que **criou** ou de que é **operador**; exclui apenas os que criou.
- **Leitor restrito:** vê apenas o que criou, aquilo de que é operador e o que foi **compartilhado com ele** (campo *Compartilhado com*).

As vulnerabilidades de um relatório seguem o acesso do relatório.`,
      },
      {
        id: 'operacoes', title: 'Operações e filtros',
        md: `A página **Operações** lista vulnerabilidades e relatórios. Clique em uma linha para ver o resumo; abra o registro para os detalhes. Marque várias linhas para ações em lote (exportar, disparar, excluir). Itens que não podem receber a ação são ignorados e informados.

Use a caixa **Filtrar**. Digite \`/\` para ver as chaves disponíveis:

- \`status:draft\`: status exato
- \`cvss:7\`: CVSS maior ou igual a 7
- \`operator:nome\`: operador atribuído
- \`id:CVE\`: identificador contém
- \`source:nuclei\`: fonte contém
- \`report:nome\`: relatório contém (\`report:none\` mostra as que não estão em relatório)
- texto livre: busca no identificador
- \`-chave:valor\`: exclui o que corresponde

Vários termos são combinados com **E**. O filtro fica no endereço da página, então você pode compartilhar o link.`,
      },
      {
        id: 'textos', title: 'Textos, imagens e anexos',
        md: `Os campos de texto usam **Markdown**. A barra do editor tem negrito, itálico, título, listas, código, link e citação; *Visualizar* mostra o resultado.

- Cole, arraste ou escolha uma **imagem** no editor: ela vira uma evidência e aparece no texto. O portal pede um nome para a imagem.
- **Anexos:** até 50 MB por arquivo (PDF, PNG, JPG, GIF, WebP, TXT, CSV, ZIP). O tipo do arquivo é verificado pelo conteúdo, não só pela extensão.
- **Notas internas** não vão para os relatórios entregues.`,
      },
      {
        id: 'exportar', title: 'Exportação',
        md: `Nas páginas de vulnerabilidade e de relatório, o botão **Exportar** reúne os formatos disponíveis: PDF e Word para vulnerabilidades; PDF, Excel e Word para relatórios. Em **Operações**, selecione várias linhas para exportar em lote (ZIP de PDFs ou uma planilha Excel).`,
      },
      {
        id: 'auditoria', title: 'Logs de auditoria', roles: ['auditor'],
        md: `Os **Logs de Auditoria** registram logins, criações, alterações, mudanças de status, disparos, exportações, leituras de anexos e liberações de reserva, com quem fez, quando e de qual IP. Filtre pelo tipo de ação.`,
      },
    ],
  },
  {
    id: 'vulnerabilidades', title: 'Vulnerabilidades',
    subs: [
      {
        id: 'vuln-criar', title: 'Criar uma vulnerabilidade',
        md: `Menu ➝ *Criar Vulnerabilidade*. Identificador, Descrição, Detalhes do Achado e Mitigação são obrigatórios para enviar. Você é o operador padrão; use **+** para adicionar outros operadores ou pessoas em *Compartilhado com*. Clique em um nome para removê-lo.`,
      },
      {
        id: 'vuln-ciclo', title: 'Ciclo de vida',
        md: `1. **Rascunho:** em edição. *Salvar rascunho* guarda sem validar tudo.
2. **Salva:** completa e pronta (*Enviar*).
3. **Disparada:** entregue (*Disparar*). O conteúdo passa a ficar fechado para edição.
4. **Reconhecida:** quando o ID do RVS é registrado na *Fila RVS*.
5. **Aguardando correção ➝ Reteste pendente ➝ Corrigida:** acompanhamento da correção. Um reteste reprovado volta para *Aguardando correção*.`,
      },
      {
        id: 'vuln-apos', title: 'Depois do disparo',
        md: `Depois do disparo, apenas operadores e notas internas continuam editáveis. Se um status foi alterado por engano, um administrador pode usar **Corrigir status**, que fica registrado na auditoria.`,
      },
      {
        id: 'vuln-conflitos', title: 'Edições simultâneas',
        md: `Se outra pessoa salvou a mesma vulnerabilidade enquanto você editava, o portal avisa e mostra a versão mais recente, sem sobrescrever o trabalho dela.`,
      },
      {
        id: 'rvs', title: 'Fila RVS',
        md: `A **Fila RVS** lista as vulnerabilidades disparadas que ainda não têm ID de RVS. Informe o ID (ex.: \`RVS-2026-001\`) para marcar a vulnerabilidade como **Reconhecida**. O ID não pode ser alterado depois.`,
      },
    ],
  },
  {
    id: 'relatorios', title: 'Relatórios e Templates',
    subs: [
      {
        id: 'rel-criar', title: 'Criar um relatório',
        md: `Menu ➝ Relatórios ➝ *Criar Relatório*. Opcionalmente, escolha um **template** para começar com textos prontos.`,
      },
      {
        id: 'rel-editar', title: 'Edição e reserva',
        md: `Clique em **Editar** para reservar o relatório. Enquanto você edita, ninguém mais altera; a reserva é liberada ao sair ou após **10 minutos** sem atividade. Se a reserva estiver com outra pessoa, o portal mostra quem é. Um administrador pode liberá-la.`,
      },
      {
        id: 'rel-conteudo', title: 'Conteúdo',
        md: `Informações Gerais, Dados do Relatório, Sumário Executivo, Introdução, Seções Adicionais (com títulos próprios, reordenáveis), as vulnerabilidades do relatório, evidências e notas internas. Fora da edição, a página mostra o conteúdo como ele aparece no relatório.`,
      },
      {
        id: 'rel-disparo', title: 'Disparo e exclusão',
        md: `Entrega o relatório com suas vulnerabilidades. Se a entrega falhar, o relatório indica a falha e pode ser disparado de novo. Só relatórios em **Rascunho** podem ser excluídos.`,
      },
      {
        id: 'templates', title: 'Templates', roles: CREATORS,
        md: `Templates são textos prontos (Sumário Executivo, Introdução e Seções Adicionais) para iniciar relatórios. Ficam em menu ➝ Relatórios ➝ *Templates*.

Um relatório copia o texto do template no momento da criação; mudanças posteriores no template não alteram relatórios já criados.`,
      },
      {
        id: 'tpl-salvar', title: 'Salvar como Template', roles: CREATORS,
        md: `Guarda o Sumário Executivo, a Introdução e as Seções Adicionais atuais como um template seu.`,
      },
      {
        id: 'tpl-compartilhar', title: 'Compartilhamento e aprovação', roles: CREATORS,
        md: `- Um template novo é **Privado**: só você o vê e usa, e pode editá-lo ou excluí-lo.
- **Solicitar compartilhamento** o envia para aprovação (**Aguardando aprovação**). A partir daí você não pode mais alterá-lo; *Cancelar solicitação* o devolve para privado.
- Um administrador **aprova** (fica **Compartilhado** e disponível para todos) ou **recusa** (volta a privado).
- Compartilhado, só administradores alteram o template. Para mudar algo, crie um novo a partir de um relatório.
- Um administrador pode **remover o compartilhamento** (**Indisponível**: ninguém o usa, nem o autor) e **compartilhar novamente** depois.`,
      },
    ],
  },
  {
    id: 'api', title: 'API', roles: CREATORS,
    subs: [
      {
        id: 'api-visao', title: 'Visão geral e endpoints',
        md: `A API permite que outros sistemas **leiam** vulnerabilidades e relatórios, **baixem** exportações, **registrem IDs de RVS** e **criem** vulnerabilidades. Ela é separada da API usada pelo próprio portal: uma chave de API **só** funciona em \`/api/v1/*\` (e no antigo \`/api/ingest/*\`).

Cada endpoint exige um **escopo** na chave:

- \`GET /api/v1/vulnerabilities\`: lista, com filtros e paginação. Escopo \`vulns:read\`.
- \`GET /api/v1/vulnerabilities/{ref}\`: uma vulnerabilidade completa. \`vulns:read\`.
- \`GET /api/v1/vulnerabilities/{ref}/attachments\`: as evidências dela. \`vulns:read\`.
- \`GET /api/v1/attachments/{id}/content\`: baixa um arquivo de evidência. \`vulns:read\` (de vulnerabilidade) ou \`reports:read\` (de relatório).
- \`GET /api/v1/vulnerabilities/{ref}/export?format=pdf|docx\`: o mesmo arquivo do botão *Exportar*. \`exports\`.
- \`GET /api/v1/rvs-queue\`: disparadas aguardando ID de RVS. \`rvs:write\` ou \`vulns:read\`.
- \`POST /api/v1/vulnerabilities/{ref}/rvs\`: registra o ID de RVS. \`rvs:write\`.
- \`POST /api/v1/vulnerabilities\`: cria uma vulnerabilidade. \`vulns:write\`.
- \`GET /api/v1/reports\`: lista de relatórios. \`reports:read\`.
- \`GET /api/v1/reports/{ref}\`: um relatório com seções, vulnerabilidades e evidências. \`reports:read\`.
- \`GET /api/v1/reports/{ref}/export?format=pdf|xlsx|docx\`: arquivos do relatório. \`exports\`.
- \`GET /api/health\`: verifica se o portal está no ar. Sem chave.

\`{ref}\` aceita o UUID ou o número do registro (\`VULN-0012\`, \`OP-0003\`), sem diferenciar maiúsculas.`,
      },
      {
        id: 'api-chaves', title: 'Chaves e escopos',
        md: `Somente um **administrador** cria chaves, em *Chaves de API*, escolhendo um nome, os **escopos** e, se quiser, uma **data de expiração**. A chave completa aparece **uma única vez**; o portal guarda só um hash e o prefixo (8 caracteres).

Escopos:

- \`vulns:read\`: ler vulnerabilidades e suas evidências.
- \`vulns:write\`: criar vulnerabilidades.
- \`rvs:write\`: ver a Fila RVS e registrar IDs de RVS.
- \`reports:read\`: ler relatórios e suas evidências.
- \`exports\`: baixar PDF, Word e Excel.

Dê a cada sistema **só o que ele usa**: um sistema de chamados que apenas registra RVS precisa só de \`rvs:write\`.

- Uma chave lê **todos** os registros que seu escopo permite; as restrições por usuário (Editor e Leitor restritos) valem para pessoas, não para sistemas.
- Fora de \`/api/v1/*\` e \`/api/ingest/*\`, nenhuma chave funciona (\`401\`), qualquer que seja o escopo.
- Chave ausente, desconhecida, revogada ou expirada recebe sempre o mesmo \`401\`. Chave sem o escopo do endpoint recebe \`403\`.
- Criações, registros de RVS, exportações e downloads de evidência ficam nos **Logs de Auditoria** com o autor \`api:<prefixo da chave>\`. Vulnerabilidades criadas pela API pertencem ao administrador que emitiu a chave.`,
      },
      {
        id: 'api-auth', title: 'Autenticação',
        md: `Envie a chave no cabeçalho \`X-API-Key\`, com corpo JSON:

\`\`\`
X-API-Key: <sua chave>
Content-Type: application/json
\`\`\``,
      },
      {
        id: 'api-leitura', title: 'Leitura, paginação e sincronização',
        md: `As listas (\`/vulnerabilities\` e \`/reports\`) vêm em ordem de **última alteração** e em páginas:

\`\`\`
{"items": [ ... ], "next_cursor": "MjAyNi0xMC0wOF..."}
\`\`\`

- \`limit\`: itens por página, de 1 a 200 (padrão 50).
- \`cursor\`: passe o \`next_cursor\` recebido para obter a próxima página. \`null\` indica o fim.
- \`updated_since\`: só o que foi criado ou alterado a partir desse momento (ISO 8601, ex. \`2026-10-25T14:00:00Z\`).

Filtros de \`/vulnerabilities\`: \`status\` (repita para vários: \`status=dispatched&status=acknowledged\`), \`source\` (contém), \`report\` (UUID, número ou \`none\` para as que não estão em relatório) e \`cvss_min\`. Filtros de \`/reports\`: \`status\` e \`client\` (contém).

**Para sincronizar** outro sistema: guarde o \`updated_at\` do último item processado e, na próxima execução, peça \`updated_since\` com esse valor, seguindo \`next_cursor\` até o fim. Um item alterado de novo volta a aparecer.

- As listas trazem um **resumo**; busque \`/{ref}\` para o conteúdo completo.
- Datas e horas estão em **UTC**.
- **Notas internas** nunca saem pela API, assim como nas exportações.`,
      },
      {
        id: 'api-rvs', title: 'Fila RVS e registro de RVS',
        md: `Um sistema de chamados pode buscar as vulnerabilidades **disparadas** que aguardam ID de RVS e devolver o ID quando o chamado for aberto:

\`\`\`
GET /api/v1/rvs-queue
POST /api/v1/vulnerabilities/VULN-0012/rvs   {"rvs_id": "RVS-2026-001"}
\`\`\`

A resposta é a vulnerabilidade completa, agora **Reconhecida**. Regras:

- Só vulnerabilidades **Disparadas** aceitam RVS; outras recebem \`409\`.
- O ID não pode ser alterado depois (\`409\` em uma segunda tentativa).`,
      },
      {
        id: 'api-criar', title: 'Criar uma vulnerabilidade',
        md: `\`POST /api/v1/vulnerabilities\`, escopo \`vulns:write\`. O antigo \`POST /api/ingest/vulnerabilities\` faz o mesmo e continua funcionando.

Corpo JSON de até **1 MB**. Todos os campos são opcionais, respeitando as regras abaixo:

- \`identifier\` (texto, até 500): CVE ou nome do achado.
- \`description\`, \`finding_detail\`, \`mitigation\` (Markdown, até 100.000 cada): Descrição, Detalhes do Achado e Mitigação.
- \`cwe\` (texto): \`CWE-79\` ou só \`79\`; é normalizado para \`CWE-79\`.
- \`cvss_score\` (número de 0 a 10) e \`cvss_vector\` (texto, até 200).
- \`references\` (lista de até 50 URLs): cada uma precisa começar com \`http://\` ou \`https://\`.
- \`source\` (texto, até 200): a ferramenta de origem, ex. \`nuclei\`, \`burp\`. Aparece em *Fontes* e no filtro \`source:\`.
- \`internal_notes\` (Markdown): notas internas.
- \`operators\` (lista de até 20 **logins**): usuários **ativos** com papel Administrador, Editor (todos) ou Editor restrito.
- \`status\`: \`"draft"\` (padrão) ou \`"saved_local"\`. A API nunca cria vulnerabilidades disparadas.
- \`metadata\` (objeto): dados livres da ferramenta, guardados como vieram. **Campos desconhecidos** no corpo também vão para os metadados. Limite: 64 KB no total.

Regras:

- Pelo menos um entre \`identifier\`, \`description\` e \`finding_detail\` deve ser preenchido.
- \`"saved_local"\` exige \`identifier\`, \`description\`, \`finding_detail\` e \`mitigation\` (os mesmos campos do botão *Enviar*) e já atribui o número \`VULN-xxxx\`.

Resposta \`201\`:

\`\`\`
{"id": "72643b23-af52-42d9-a139-c1aea6f70a15", "internal_id": null, "status": "draft"}
\`\`\`

\`id\` identifica a vulnerabilidade (\`/vulnerabilities/<id>\` no portal). \`internal_id\` é o número \`VULN-xxxx\`, presente apenas quando o status é \`saved_local\`.`,
      },
      {
        id: 'api-exemplos', title: 'Exemplos',
        md: `Ler uma vulnerabilidade pelo número:

\`\`\`
curl -sS https://<portal>/api/v1/vulnerabilities/VULN-0002 -H "X-API-Key: $PORTAL_KEY"
# {"id": "08ff5461-…", "internal_id": "VULN-0002", "status": "fixed",
#  "identifier": "SSRF - app-mobile", "cwe": "CWE-918", "rvs_id": "RVS-2026-1004",
#  "operators": ["jonathan"], "fixed_at": "2026-10-08T12:59:30.244446", ...}
\`\`\`

Sincronizar o que mudou (Python):

\`\`\`
import os, requests

API = "https://<portal>/api/v1"
H = {"X-API-Key": os.environ["PORTAL_KEY"]}

def changed_since(since):
    params = {"updated_since": since, "limit": 200}
    while True:
        page = requests.get(f"{API}/vulnerabilities", headers=H, params=params, timeout=30).json()
        yield from page["items"]
        if not page["next_cursor"]:
            break
        params["cursor"] = page["next_cursor"]

for v in changed_since("2026-10-25T00:00:00Z"):
    print(v["internal_id"], v["status"], v["updated_at"])
\`\`\`

Registrar um RVS:

\`\`\`
curl -sS -X POST https://<portal>/api/v1/vulnerabilities/VULN-0012/rvs \\
  -H "X-API-Key: $PORTAL_KEY" -H "Content-Type: application/json" \\
  -d '{"rvs_id": "RVS-2026-001"}'
\`\`\`

Baixar o PDF de um relatório:

\`\`\`
curl -sS -o OP-0001.pdf "https://<portal>/api/v1/reports/OP-0001/export?format=pdf" \\
  -H "X-API-Key: $PORTAL_KEY"
\`\`\`

Criar um rascunho a partir de um scanner (o campo \`host\`, desconhecido, vai para os metadados):

\`\`\`
curl -sS -X POST https://<portal>/api/v1/vulnerabilities \\
  -H "X-API-Key: $PORTAL_KEY" -H "Content-Type: application/json" \\
  -d '{"identifier": "Exposed .git directory", "source": "nuclei", "cwe": "527",
       "cvss_score": 5.3, "operators": ["jonathan"], "host": "app.example.com"}'
# 201 {"id":"…","internal_id":null,"status":"draft"}
\`\`\``,
      },
      {
        id: 'api-erros', title: 'Erros',
        md: `O corpo de erro sempre traz \`detail\`: um texto ou, em erros de formato, uma lista com o campo e o motivo.

- \`401\`: chave ausente, inválida, revogada ou expirada. \`{"detail": "Invalid or missing API key"}\`
- \`403\`: a chave não tem o escopo do endpoint. \`{"detail": "This API key lacks the scope 'rvs:write'"}\`
- \`404\`: o registro não existe (ou foi excluído).
- \`409\`: a ação não cabe no status atual, ex. RVS em vulnerabilidade não disparada ou já registrado.
- \`413\`: corpo acima de 1 MB.
- \`422\`: dados ou parâmetros inválidos (inclusive \`cursor\` inválido). Exemplos:

\`\`\`
{"detail": "Required for status 'saved_local': description, finding_detail, mitigation"}
{"detail": "unknown operator(s): nobody; operator(s) not active writers: isabella"}
{"detail": [{"loc": ["body", "cvss_score"], "msg": "Input should be less than or equal to 10", ...}]}
\`\`\``,
      },
      {
        id: 'api-praticas', title: 'Boas práticas',
        md: `- Uma chave por sistema, só com os escopos que ele usa e com data de expiração. Revogue as que não forem mais usadas.
- Nunca coloque a chave no código ou em repositórios: leia de uma variável de ambiente ou de um cofre.
- Para sincronizar, use \`updated_since\` + \`next_cursor\` em vez de baixar tudo a cada execução.
- **Não há deduplicação** na criação: repetir a mesma requisição cria outro registro. Depois de um erro de rede, confira (filtro \`source\`) antes de reenviar.
- Envie como \`draft\` quando um analista ainda precisa revisar o achado.`,
      },
    ],
  },
  {
    id: 'gerenciamento', title: 'Gerenciamento', roles: ['admin'],
    subs: [
      {
        id: 'adm-usuarios', title: 'Usuários',
        md: `Menu ➝ *Usuários*. Busque pelo login e filtre por papel ou situação; o usuário selecionado fica no endereço da página.

- **Novo usuário:** informe login, uma senha temporária e o papel. No primeiro acesso, o usuário é obrigado a trocar a senha.
- **Papel:** altere na ficha do usuário; vale imediatamente.
- **Redefinir senha:** define uma nova senha temporária e obriga a troca no próximo acesso. Sessões abertas desse usuário ficam bloqueadas até a troca.
- **Desativar:** bloqueia o acesso na hora, inclusive de sessões abertas. Você não pode desativar a si mesmo.`,
      },
      {
        id: 'adm-acesso', title: 'Acesso de cada usuário',
        md: `Na ficha do usuário, a lista de acesso mostra quais vulnerabilidades e relatórios ele alcança e **por quê**: *Criou*, *Operador*, *Compartilhado* (campo *Compartilhado com*) ou *Via relatório* (vulnerabilidades de um relatório que ele acessa).

Para papéis com acesso total (Administrador, Editor e Leitor todos, Auditor) a ficha informa que o usuário vê tudo. Use essa lista para conferir o que um **Editor restrito** ou **Leitor restrito** pode ver antes de compartilhar algo.`,
      },
      {
        id: 'adm-chaves', title: 'Chaves de API',
        md: `Menu ➝ *Chaves de API*. Crie uma chave por sistema, com um nome que o identifique, **só os escopos que ele usa** e, de preferência, uma data de expiração.

- A chave completa aparece **uma única vez**, logo após a criação: copie e entregue ao responsável pelo sistema por um canal seguro. Depois, o portal mostra só o prefixo.
- A lista mostra os escopos, a expiração e o último uso de cada chave.
- **Revogar** desativa a chave na hora; revogue as que não forem mais usadas ou que possam ter vazado.

Escopos e endpoints na seção **API**.`,
      },
      {
        id: 'adm-templates', title: 'Aprovação de templates',
        md: `Em *Templates*, o atalho **N aguardando aprovação** lista as solicitações de compartilhamento. Abra cada template para ler o conteúdo e então:

- **Aprovar:** o template fica *Compartilhado* e disponível para todos.
- **Recusar:** volta a *Privado* para o autor, que pode ajustá-lo e pedir de novo.
- **Remover compartilhamento:** deixa um template compartilhado *Indisponível* para todos, inclusive o autor. **Compartilhar novamente** o reativa.

Como administrador, você vê todos os templates e pode editar ou excluir qualquer um.`,
      },
      {
        id: 'adm-reservas', title: 'Reservas de relatório',
        md: `Quando alguém está editando um relatório, a página mostra quem tem a reserva e desde quando. Se a pessoa saiu sem liberar, a reserva expira sozinha após 10 minutos sem atividade.

Para liberar antes, use **Liberar bloqueio** na página do relatório. As alterações não salvas de quem tinha a reserva são perdidas, e a ação fica registrada na auditoria.`,
      },
      {
        id: 'adm-auditoria', title: 'Logs de auditoria',
        md: `Menu ➝ *Logs de Auditoria*. Registra logins, criações, alterações, mudanças de status, disparos, exportações, leituras de anexos e liberações de reserva, com quem fez (usuário ou \`api:<prefixo>\` para chaves), quando e de qual IP. Filtre pelo tipo de ação.`,
      },
    ],
  },
]

const en = [
  {
    id: 'geral', title: 'General Information',
    subs: [
      {
        id: 'inicio', title: 'Getting started',
        md: `The portal holds the **vulnerabilities** found by the Red Team and the **reports** delivered to the teams responsible for them.

- **Left menu:** the icons lead to each area. The ☰ button at the top opens the menu with names. **Reports** holds *Create Report* and *Templates*: hover over its icon to choose.
- **Your username (top right):** language, this documentation, your profile, sign out and the session time left.
- The menu shows only what your role can use. If something is missing, you don't have access to it.`,
      },
      {
        id: 'sessao', title: 'Session',
        md: `- A session lasts at most **1 hour** from sign-in and ends sooner after **15 minutes without activity** (mouse, keyboard or scrolling, in any portal tab).
- In your user menu, **Session mm:ss / mm:ss** shows the time left: first until the inactivity limit, then until the 1-hour end.
- **2 minutes** before the inactivity limit you see *"Are you still there?"*: click **Stay signed in**.
- **5 minutes** before the 1-hour end, the portal reminds you to save what you are editing.
- If the session ends with **unsaved changes**, the page stays open and the portal asks for your password again. After signing in, save as usual. **Discard and leave** drops the changes.
- On your first sign-in, or after an administrator resets your password, you must change it in **Profile** before going on.`,
      },
      {
        id: 'papeis', title: 'Roles and access',
        md: `Each user has a role, set by an administrator:

- **Administrator:** sees and changes everything; manages users, API keys and template sharing.
- **Editor (all):** sees and changes every vulnerability and report.
- **Reader (all):** sees everything, changes nothing.
- **Auditor:** sees everything and reads the audit logs.
- **Restricted editor:** creates vulnerabilities and reports; sees and changes the ones they **created** or **operate**; deletes only the ones they created.
- **Restricted reader:** sees only what they created, what they operate and what was **shared with them** (*Shared with* field).

A report's vulnerabilities follow the report's access.`,
      },
      {
        id: 'operacoes', title: 'Operations and filters',
        md: `The **Operations** page lists vulnerabilities and reports. Click a row for a summary; open the record for its details. Tick several rows for batch actions (export, dispatch, delete). Items the action doesn't apply to are skipped and reported.

Use the **Filter** box. Type \`/\` to see the keys:

- \`status:draft\`: exact status
- \`cvss:7\`: CVSS 7 or higher
- \`operator:name\`: assigned operator
- \`id:CVE\`: identifier contains
- \`source:nuclei\`: source contains
- \`report:name\`: report contains (\`report:none\` shows those outside any report)
- free text: searches the identifier
- \`-key:value\`: excludes matches

Several terms combine with **AND**. The filter is kept in the page address, so you can share the link.`,
      },
      {
        id: 'textos', title: 'Text, images and attachments',
        md: `Text fields use **Markdown**. The editor bar has bold, italic, heading, lists, code, link and quote; *Preview* shows the result.

- Paste, drop or pick an **image** in the editor: it becomes evidence and shows in the text. The portal asks for a name for it.
- **Attachments:** up to 50 MB per file (PDF, PNG, JPG, GIF, WebP, TXT, CSV, ZIP). The file type is checked by its content, not only its extension.
- **Internal notes** never go into delivered reports.`,
      },
      {
        id: 'exportar', title: 'Export',
        md: `On vulnerability and report pages, the **Export** button gathers the formats: PDF and Word for vulnerabilities; PDF, Excel and Word for reports. In **Operations**, tick several rows to export in batch (a ZIP of PDFs or an Excel sheet).`,
      },
      {
        id: 'auditoria', title: 'Audit logs', roles: ['auditor'],
        md: `The **Audit Logs** record sign-ins, creations, changes, status changes, dispatches, exports, attachment reads and reservation releases, with who did it, when and from which IP. Filter by type of action.`,
      },
    ],
  },
  {
    id: 'vulnerabilidades', title: 'Vulnerabilities',
    subs: [
      {
        id: 'vuln-criar', title: 'Create a vulnerability',
        md: `Menu ➝ *Create Vulnerability*. Identifier, Description, Finding Details and Mitigation are required to send it. You are the default operator; use **+** to add operators or people in *Shared with*. Click a name to remove it.`,
      },
      {
        id: 'vuln-ciclo', title: 'Lifecycle',
        md: `1. **Draft:** being written. *Save draft* keeps it without full validation.
2. **Saved:** complete and ready (*Send*).
3. **Dispatched:** delivered (*Dispatch*). Its content is now closed for editing.
4. **Acknowledged:** once the RVS ID is recorded in the *RVS Queue*.
5. **Waiting fix ➝ Retest pending ➝ Fixed:** follow-up of the fix. A failed retest goes back to *Waiting fix*.`,
      },
      {
        id: 'vuln-apos', title: 'After dispatch',
        md: `After dispatch only operators and internal notes stay editable. If a status was changed by mistake, an administrator can use **Correct status**, which is recorded in the audit log.`,
      },
      {
        id: 'vuln-conflitos', title: 'Simultaneous edits',
        md: `If someone else saved the same vulnerability while you were editing, the portal tells you and shows the latest version instead of overwriting their work.`,
      },
      {
        id: 'rvs', title: 'RVS Queue',
        md: `The **RVS Queue** lists dispatched vulnerabilities that have no RVS ID yet. Enter the ID (e.g. \`RVS-2026-001\`) to mark the vulnerability **Acknowledged**. The ID can't be changed afterwards.`,
      },
    ],
  },
  {
    id: 'relatorios', title: 'Reports & Templates',
    subs: [
      {
        id: 'rel-criar', title: 'Create a report',
        md: `Menu ➝ Reports ➝ *Create Report*. Optionally pick a **template** to start from ready-made text.`,
      },
      {
        id: 'rel-editar', title: 'Editing and reservation',
        md: `Click **Edit** to reserve the report. While you edit, nobody else can change it; the reservation is released when you leave or after **10 minutes** without activity. If someone else holds it, the portal shows who. An administrator can release it.`,
      },
      {
        id: 'rel-conteudo', title: 'Content',
        md: `General Information, Report Data, Executive Summary, Introduction, Additional Sections (with their own titles, reorderable), the report's vulnerabilities, evidence and internal notes. Outside editing, the page shows the content as it reads in the report.`,
      },
      {
        id: 'rel-disparo', title: 'Dispatch and deletion',
        md: `Delivers the report with its vulnerabilities. If delivery fails, the report says so and can be dispatched again. Only **Draft** reports can be deleted.`,
      },
      {
        id: 'templates', title: 'Templates', roles: CREATORS,
        md: `Templates are ready-made text (Executive Summary, Introduction and Additional Sections) to start reports from. They live in menu ➝ Reports ➝ *Templates*.

A report copies the template's text when it is created; later changes to the template don't touch existing reports.`,
      },
      {
        id: 'tpl-salvar', title: 'Save as Template', roles: CREATORS,
        md: `Keeps the current Executive Summary, Introduction and Additional Sections as a template of yours.`,
      },
      {
        id: 'tpl-compartilhar', title: 'Sharing and approval', roles: CREATORS,
        md: `- A new template is **Private**: only you see and use it, and you can edit or delete it.
- **Request sharing** sends it for approval (**Awaiting approval**). From then on you can't change it; *Cancel request* makes it private again.
- An administrator **approves** it (**Shared**, available to everyone) or **rejects** it (back to private).
- Once shared, only administrators change it. To change something, create a new one from a report.
- An administrator can **unshare** it (**Unavailable**: nobody uses it, its author included) and **share it again** later.`,
      },
    ],
  },
  {
    id: 'api', title: 'API', roles: CREATORS,
    subs: [
      {
        id: 'api-visao', title: 'Overview and endpoints',
        md: `The API lets other systems **read** vulnerabilities and reports, **download** exports, **record RVS IDs** and **create** vulnerabilities. It is separate from the API the portal itself uses: an API key works **only** on \`/api/v1/*\` (and the older \`/api/ingest/*\`).

Each endpoint needs a **scope** on the key:

- \`GET /api/v1/vulnerabilities\`: list, with filters and paging. Scope \`vulns:read\`.
- \`GET /api/v1/vulnerabilities/{ref}\`: one complete vulnerability. \`vulns:read\`.
- \`GET /api/v1/vulnerabilities/{ref}/attachments\`: its evidence. \`vulns:read\`.
- \`GET /api/v1/attachments/{id}/content\`: downloads an evidence file. \`vulns:read\` (a vulnerability's) or \`reports:read\` (a report's).
- \`GET /api/v1/vulnerabilities/{ref}/export?format=pdf|docx\`: the same file as the *Export* button. \`exports\`.
- \`GET /api/v1/rvs-queue\`: dispatched ones waiting for an RVS ID. \`rvs:write\` or \`vulns:read\`.
- \`POST /api/v1/vulnerabilities/{ref}/rvs\`: records the RVS ID. \`rvs:write\`.
- \`POST /api/v1/vulnerabilities\`: creates a vulnerability. \`vulns:write\`.
- \`GET /api/v1/reports\`: list of reports. \`reports:read\`.
- \`GET /api/v1/reports/{ref}\`: one report with sections, vulnerabilities and evidence. \`reports:read\`.
- \`GET /api/v1/reports/{ref}/export?format=pdf|xlsx|docx\`: report files. \`exports\`.
- \`GET /api/health\`: checks the portal is up. No key.

\`{ref}\` takes the UUID or the record's number (\`VULN-0012\`, \`OP-0003\`), case-insensitive.`,
      },
      {
        id: 'api-chaves', title: 'Keys and scopes',
        md: `Only an **administrator** creates keys, under *API Keys*, choosing a name, the **scopes** and, optionally, an **expiry date**. The full key is shown **only once**; the portal keeps only a hash and the prefix (8 characters).

Scopes:

- \`vulns:read\`: read vulnerabilities and their evidence.
- \`vulns:write\`: create vulnerabilities.
- \`rvs:write\`: see the RVS queue and record RVS IDs.
- \`reports:read\`: read reports and their evidence.
- \`exports\`: download PDF, Word and Excel.

Give each system **only what it uses**: a ticketing system that only records RVS IDs needs just \`rvs:write\`.

- A key reads **every** record its scope allows; per-user restrictions (Restricted editor and reader) apply to people, not systems.
- Outside \`/api/v1/*\` and \`/api/ingest/*\`, no key works (\`401\`), whatever its scopes.
- A missing, unknown, revoked or expired key always gets the same \`401\`. A key without the endpoint's scope gets \`403\`.
- Creations, RVS records, exports and evidence downloads are in the **Audit Logs** with the actor \`api:<key prefix>\`. Vulnerabilities created through the API belong to the administrator who issued the key.`,
      },
      {
        id: 'api-auth', title: 'Authentication',
        md: `Send the key in the \`X-API-Key\` header, with a JSON body:

\`\`\`
X-API-Key: <your key>
Content-Type: application/json
\`\`\``,
      },
      {
        id: 'api-leitura', title: 'Reading, paging and syncing',
        md: `Lists (\`/vulnerabilities\` and \`/reports\`) come in **last-change** order and in pages:

\`\`\`
{"items": [ ... ], "next_cursor": "MjAyNi0xMC0wOF..."}
\`\`\`

- \`limit\`: items per page, 1 to 200 (default 50).
- \`cursor\`: pass the \`next_cursor\` you got to fetch the next page. \`null\` means the end.
- \`updated_since\`: only what was created or changed from that moment on (ISO 8601, e.g. \`2026-10-25T14:00:00Z\`).

\`/vulnerabilities\` filters: \`status\` (repeat for several: \`status=dispatched&status=acknowledged\`), \`source\` (contains), \`report\` (UUID, number, or \`none\` for those outside any report) and \`cvss_min\`. \`/reports\` filters: \`status\` and \`client\` (contains).

**To sync** another system: keep the \`updated_at\` of the last item you processed and, on the next run, ask for \`updated_since\` with that value, following \`next_cursor\` to the end. An item changed again shows up again.

- Lists carry a **summary**; fetch \`/{ref}\` for the full content.
- Dates and times are in **UTC**.
- **Internal notes** never leave through the API, as in the exports.`,
      },
      {
        id: 'api-rvs', title: 'RVS queue and RVS IDs',
        md: `A ticketing system can fetch the **dispatched** vulnerabilities waiting for an RVS ID and send the ID back once its ticket is open:

\`\`\`
GET /api/v1/rvs-queue
POST /api/v1/vulnerabilities/VULN-0012/rvs   {"rvs_id": "RVS-2026-001"}
\`\`\`

The response is the full vulnerability, now **Acknowledged**. Rules:

- Only **Dispatched** vulnerabilities take an RVS ID; others get \`409\`.
- The ID can't be changed afterwards (\`409\` on a second try).`,
      },
      {
        id: 'api-criar', title: 'Create a vulnerability',
        md: `\`POST /api/v1/vulnerabilities\`, scope \`vulns:write\`. The older \`POST /api/ingest/vulnerabilities\` does the same and keeps working.

JSON body of up to **1 MB**. Every field is optional, under the rules below:

- \`identifier\` (text, up to 500): CVE or name of the finding.
- \`description\`, \`finding_detail\`, \`mitigation\` (Markdown, up to 100,000 each): Description, Finding Details and Mitigation.
- \`cwe\` (text): \`CWE-79\` or just \`79\`; normalised to \`CWE-79\`.
- \`cvss_score\` (number 0 to 10) and \`cvss_vector\` (text, up to 200).
- \`references\` (list of up to 50 URLs): each must start with \`http://\` or \`https://\`.
- \`source\` (text, up to 200): the tool it came from, e.g. \`nuclei\`, \`burp\`. Shown in *Sources* and the \`source:\` filter.
- \`internal_notes\` (Markdown): internal notes.
- \`operators\` (list of up to 20 **usernames**): **active** users with role Administrator, Editor (all) or Restricted editor.
- \`status\`: \`"draft"\` (default) or \`"saved_local"\`. The API never creates dispatched vulnerabilities.
- \`metadata\` (object): free data from the tool, stored as sent. **Unknown fields** in the body go to the metadata too. Limit: 64 KB in total.

Rules:

- At least one of \`identifier\`, \`description\` and \`finding_detail\` must be filled in.
- \`"saved_local"\` needs \`identifier\`, \`description\`, \`finding_detail\` and \`mitigation\` (the same fields as the *Send* button) and assigns the \`VULN-xxxx\` number at once.

\`201\` response:

\`\`\`
{"id": "72643b23-af52-42d9-a139-c1aea6f70a15", "internal_id": null, "status": "draft"}
\`\`\`

\`id\` identifies the vulnerability (\`/vulnerabilities/<id>\` in the portal). \`internal_id\` is the \`VULN-xxxx\` number, present only when the status is \`saved_local\`.`,
      },
      {
        id: 'api-exemplos', title: 'Examples',
        md: `Read a vulnerability by its number:

\`\`\`
curl -sS https://<portal>/api/v1/vulnerabilities/VULN-0002 -H "X-API-Key: $PORTAL_KEY"
# {"id": "08ff5461-…", "internal_id": "VULN-0002", "status": "fixed",
#  "identifier": "SSRF - app-mobile", "cwe": "CWE-918", "rvs_id": "RVS-2026-1004",
#  "operators": ["jonathan"], "fixed_at": "2026-10-08T12:59:30.244446", ...}
\`\`\`

Sync what changed (Python):

\`\`\`
import os, requests

API = "https://<portal>/api/v1"
H = {"X-API-Key": os.environ["PORTAL_KEY"]}

def changed_since(since):
    params = {"updated_since": since, "limit": 200}
    while True:
        page = requests.get(f"{API}/vulnerabilities", headers=H, params=params, timeout=30).json()
        yield from page["items"]
        if not page["next_cursor"]:
            break
        params["cursor"] = page["next_cursor"]

for v in changed_since("2026-10-25T00:00:00Z"):
    print(v["internal_id"], v["status"], v["updated_at"])
\`\`\`

Record an RVS ID:

\`\`\`
curl -sS -X POST https://<portal>/api/v1/vulnerabilities/VULN-0012/rvs \\
  -H "X-API-Key: $PORTAL_KEY" -H "Content-Type: application/json" \\
  -d '{"rvs_id": "RVS-2026-001"}'
\`\`\`

Download a report's PDF:

\`\`\`
curl -sS -o OP-0001.pdf "https://<portal>/api/v1/reports/OP-0001/export?format=pdf" \\
  -H "X-API-Key: $PORTAL_KEY"
\`\`\`

Create a draft from a scanner (the unknown \`host\` field goes to the metadata):

\`\`\`
curl -sS -X POST https://<portal>/api/v1/vulnerabilities \\
  -H "X-API-Key: $PORTAL_KEY" -H "Content-Type: application/json" \\
  -d '{"identifier": "Exposed .git directory", "source": "nuclei", "cwe": "527",
       "cvss_score": 5.3, "operators": ["jonathan"], "host": "app.example.com"}'
# 201 {"id":"…","internal_id":null,"status":"draft"}
\`\`\``,
      },
      {
        id: 'api-erros', title: 'Errors',
        md: `The error body always has \`detail\`: a text or, for format errors, a list with the field and the reason.

- \`401\`: missing, invalid, revoked or expired key. \`{"detail": "Invalid or missing API key"}\`
- \`403\`: the key lacks the endpoint's scope. \`{"detail": "This API key lacks the scope 'rvs:write'"}\`
- \`404\`: the record doesn't exist (or was deleted).
- \`409\`: the action doesn't fit the current status, e.g. an RVS ID on a vulnerability not dispatched, or already set.
- \`413\`: body over 1 MB.
- \`422\`: invalid data or parameters (an invalid \`cursor\` included). Examples:

\`\`\`
{"detail": "Required for status 'saved_local': description, finding_detail, mitigation"}
{"detail": "unknown operator(s): nobody; operator(s) not active writers: isabella"}
{"detail": [{"loc": ["body", "cvss_score"], "msg": "Input should be less than or equal to 10", ...}]}
\`\`\``,
      },
      {
        id: 'api-praticas', title: 'Good practice',
        md: `- One key per system, with only the scopes it uses and an expiry date. Revoke keys no longer in use.
- Never put the key in code or repositories: read it from an environment variable or a vault.
- To sync, use \`updated_since\` + \`next_cursor\` instead of downloading everything on each run.
- **There is no de-duplication** on create: repeating a request creates another record. After a network error, check (\`source\` filter) before sending again.
- Send as \`draft\` when an analyst still needs to review the finding.`,
      },
    ],
  },
  {
    id: 'gerenciamento', title: 'Management', roles: ['admin'],
    subs: [
      {
        id: 'adm-usuarios', title: 'Users',
        md: `Menu ➝ *Users*. Search by username and filter by role or state; the selected user is kept in the page address.

- **New user:** enter a username, a temporary password and the role. On first sign-in the user must change the password.
- **Role:** change it in the user's panel; it applies at once.
- **Reset password:** sets a new temporary password and forces a change at the next sign-in. That user's open sessions are blocked until they change it.
- **Deactivate:** blocks access at once, open sessions included. You cannot deactivate yourself.`,
      },
      {
        id: 'adm-acesso', title: 'Each user\'s access',
        md: `In the user's panel, the access list shows which vulnerabilities and reports they reach and **why**: *Created*, *Operator*, *Shared* (*Shared with* field) or *Via report* (vulnerabilities of a report they can open).

For roles with full access (Administrator, Editor and Reader all, Auditor) the panel says the user sees everything. Use the list to check what a **Restricted editor** or **Restricted reader** can see before sharing something.`,
      },
      {
        id: 'adm-chaves', title: 'API keys',
        md: `Menu ➝ *API Keys*. Create one key per system, with a name that identifies it, **only the scopes it uses** and, preferably, an expiry date.

- The full key is shown **only once**, right after creation: copy it and hand it to the system's owner over a safe channel. Afterwards the portal shows only its prefix.
- The list shows each key's scopes, expiry and last use.
- **Revoke** disables a key at once; revoke keys no longer in use or that may have leaked.

Scopes and endpoints in the **API** section.`,
      },
      {
        id: 'adm-templates', title: 'Template approval',
        md: `In *Templates*, the **N awaiting approval** shortcut lists the sharing requests. Open each template to read it, then:

- **Approve:** the template becomes *Shared* and available to everyone.
- **Reject:** back to *Private* for its author, who can adjust it and ask again.
- **Unshare:** makes a shared template *Unavailable* to everyone, its author included. **Share again** brings it back.

As an administrator you see every template and can edit or delete any of them.`,
      },
      {
        id: 'adm-reservas', title: 'Report reservations',
        md: `While someone edits a report, the page shows who holds the reservation and since when. If they left without releasing it, it expires by itself after 10 minutes without activity.

To release it sooner, use **Release lock** on the report page. The holder's unsaved changes are lost, and the action is recorded in the audit log.`,
      },
      {
        id: 'adm-auditoria', title: 'Audit logs',
        md: `Menu ➝ *Audit Logs*. Records sign-ins, creations, changes, status changes, dispatches, exports, attachment reads and reservation releases, with who did it (a user, or \`api:<prefix>\` for keys), when and from which IP. Filter by type of action.`,
      },
    ],
  },
]

export const DOCS = { 'pt-BR': pt, en }
