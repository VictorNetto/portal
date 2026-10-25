// User documentation shown on the Documentação page (/docs).
// Each section is Markdown rendered by MarkdownView. `roles` limits a section to
// the roles that can use what it describes (the page hides the rest, like the nav).

const CREATORS = ['admin', 'write_all', 'write_restricted']

const pt = [
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
    id: 'vulnerabilidades', title: 'Vulnerabilidades',
    md: `**Criar:** menu ➝ *Criar Vulnerabilidade*. Identificador, Descrição, Detalhes do Achado e Mitigação são obrigatórios para enviar. Você é o operador padrão; use **+** para adicionar outros operadores ou pessoas em *Compartilhado com*. Clique em um nome para removê-lo.

**Ciclo de vida:**

1. **Rascunho:** em edição. *Salvar rascunho* guarda sem validar tudo.
2. **Salva:** completa e pronta (*Enviar*).
3. **Disparada:** entregue (*Disparar*). O conteúdo passa a ficar fechado para edição.
4. **Reconhecida:** quando o ID do RVS é registrado na *Fila RVS*.
5. **Aguardando correção ➝ Reteste pendente ➝ Corrigida:** acompanhamento da correção. Um reteste reprovado volta para *Aguardando correção*.

Depois do disparo, apenas operadores e notas internas continuam editáveis. Se um status foi alterado por engano, um administrador pode usar **Corrigir status**, que fica registrado na auditoria.

Se outra pessoa salvou a mesma vulnerabilidade enquanto você editava, o portal avisa e mostra a versão mais recente, sem sobrescrever o trabalho dela.`,
  },
  {
    id: 'rvs', title: 'Fila RVS',
    md: `A **Fila RVS** lista as vulnerabilidades disparadas que ainda não têm ID de RVS. Informe o ID (ex.: \`RVS-2026-001\`) para marcar a vulnerabilidade como **Reconhecida**. O ID não pode ser alterado depois.`,
  },
  {
    id: 'relatorios', title: 'Relatórios',
    md: `**Criar:** menu ➝ Relatórios ➝ *Criar Relatório*. Opcionalmente, escolha um **template** para começar com textos prontos.

**Editar:** clique em **Editar** para reservar o relatório. Enquanto você edita, ninguém mais altera; a reserva é liberada ao sair ou após **10 minutos** sem atividade. Se a reserva estiver com outra pessoa, o portal mostra quem é. Um administrador pode liberá-la.

**Conteúdo:** Informações Gerais, Dados do Relatório, Sumário Executivo, Introdução, Seções Adicionais (com títulos próprios, reordenáveis), as vulnerabilidades do relatório, evidências e notas internas. Fora da edição, a página mostra o conteúdo como ele aparece no relatório.

**Disparar:** entrega o relatório com suas vulnerabilidades. Se a entrega falhar, o relatório indica a falha e pode ser disparado de novo. Só relatórios em **Rascunho** podem ser excluídos.

**Salvar como Template:** guarda o Sumário Executivo, a Introdução e as Seções Adicionais atuais como um template seu.`,
  },
  {
    id: 'templates', title: 'Templates', roles: CREATORS,
    md: `Templates são textos prontos (Sumário Executivo, Introdução e Seções Adicionais) para iniciar relatórios. Ficam em menu ➝ Relatórios ➝ *Templates*.

- Um template novo é **Privado**: só você o vê e usa, e pode editá-lo ou excluí-lo.
- **Solicitar compartilhamento** o envia para aprovação (**Aguardando aprovação**). A partir daí você não pode mais alterá-lo; *Cancelar solicitação* o devolve para privado.
- Um administrador **aprova** (fica **Compartilhado** e disponível para todos) ou **recusa** (volta a privado).
- Compartilhado, só administradores alteram o template. Para mudar algo, crie um novo a partir de um relatório.
- Um administrador pode **remover o compartilhamento** (**Indisponível**: ninguém o usa, nem o autor) e **compartilhar novamente** depois.

Um relatório copia o texto do template no momento da criação; mudanças posteriores no template não alteram relatórios já criados.`,
  },
  {
    id: 'textos', title: 'Textos, imagens e anexos',
    md: `Os campos de texto usam **Markdown**. A barra do editor tem negrito, itálico, título, listas, código, link e citação; *Visualizar* mostra o resultado.

- Cole, arraste ou escolha uma **imagem** no editor: ela vira uma evidência e aparece no texto. O portal pede um nome para a imagem.
- **Anexos:** até 50 MB por arquivo (PDF, PNG, JPG, GIF, WebP, TXT, CSV, ZIP). O tipo do arquivo é verificado pelo conteúdo, não só pela extensão.
- **Notas internas** não vão para os relatórios entregues.`,
  },
  {
    id: 'exportar', title: 'Exportar',
    md: `Nas páginas de vulnerabilidade e de relatório, o botão **Exportar** reúne os formatos disponíveis: PDF e Word para vulnerabilidades; PDF, Excel e Word para relatórios. Em **Operações**, selecione várias linhas para exportar em lote (ZIP de PDFs ou uma planilha Excel).`,
  },
  {
    id: 'api', title: 'API de integração', roles: CREATORS,
    md: `A API permite que ferramentas (scanners, C2, pipelines de recon) **criem vulnerabilidades** no portal sem passar pela interface. Ela é separada da API usada pelo próprio portal: uma chave de API **só** funciona nos endpoints \`/api/ingest/*\`.

### Endpoints

- \`POST /api/ingest/vulnerabilities\`: cria uma vulnerabilidade (em *Rascunho* ou *Salva*). Exige chave de API.
- \`GET /api/health\`: verifica se o portal está no ar. Não exige chave. Resposta: \`{"status": "ok", ...}\`.

### Chaves e papéis

Somente um **administrador** cria chaves, em *Chaves de API*. Peça uma ao administrador informando para que ferramenta ela será usada. A chave é exibida **uma única vez**, na criação: guarde-a em um cofre de segredos. O portal mantém apenas um hash e o prefixo (8 caracteres) para identificação.

Cada chave tem um **papel**, que limita o que ela pode fazer:

- **Editor (todos)** ou **Administrador**: podem criar vulnerabilidades. Prefira *Editor (todos)*, o mínimo necessário.
- **Leitor (todos)** ou **Auditor**: não criam nada (\`403\`). Hoje não há endpoints de leitura para chaves.
- Qualquer que seja o papel, a chave **não** acessa usuários, relatórios, chaves nem a auditoria: fora de \`/api/ingest/*\` a resposta é \`401\`.
- A chave pode ter **data de expiração** e pode ser **revogada** a qualquer momento. Chave ausente, desconhecida, revogada ou expirada recebe sempre o mesmo \`401\`.
- A vulnerabilidade criada pertence ao administrador que emitiu a chave. Nos **Logs de Auditoria**, o autor aparece como \`api:<prefixo da chave>\`.

### Autenticação

Envie a chave no cabeçalho \`X-API-Key\`, com corpo JSON:

\`\`\`
X-API-Key: <sua chave>
Content-Type: application/json
\`\`\`

### POST /api/ingest/vulnerabilities

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

\`id\` identifica a vulnerabilidade (\`/vulnerabilities/<id>\` no portal). \`internal_id\` é o número \`VULN-xxxx\`, presente apenas quando o status é \`saved_local\`.

### Exemplos

Rascunho vindo de um scanner (o campo \`host\`, desconhecido, vai para os metadados):

\`\`\`
curl -sS -X POST https://<portal>/api/ingest/vulnerabilities \\
  -H "X-API-Key: $PORTAL_KEY" -H "Content-Type: application/json" \\
  -d '{
        "identifier": "Exposed .git directory",
        "source": "nuclei",
        "cwe": "527",
        "cvss_score": 5.3,
        "references": ["https://cwe.mitre.org/data/definitions/527.html"],
        "operators": ["jonathan"],
        "host": "app.example.com"
      }'
# 201 {"id":"…","internal_id":null,"status":"draft"}
\`\`\`

Vulnerabilidade completa, já **Salva**:

\`\`\`
curl -sS -X POST https://<portal>/api/ingest/vulnerabilities \\
  -H "X-API-Key: $PORTAL_KEY" -H "Content-Type: application/json" \\
  -d '{
        "status": "saved_local",
        "identifier": "SQL injection em /login",
        "description": "O parâmetro **user** é concatenado na consulta.",
        "finding_detail": "Payload: 1 OR 1=1",
        "mitigation": "Usar consultas parametrizadas.",
        "cvss_score": 9.8,
        "source": "burp"
      }'
# 201 {"id":"…","internal_id":"VULN-0533","status":"saved_local"}
\`\`\`

Python:

\`\`\`
import os, requests

resp = requests.post(
    "https://<portal>/api/ingest/vulnerabilities",
    headers={"X-API-Key": os.environ["PORTAL_KEY"]},
    json={"identifier": "Open redirect", "source": "custom-scanner",
          "metadata": {"scan_id": "2026-10-25-01"}},
    timeout=30,
)
resp.raise_for_status()
print(resp.json()["id"])
\`\`\`

### Erros

O corpo de erro sempre traz \`detail\`: um texto ou, em erros de formato, uma lista com o campo e o motivo.

- \`401\`: chave ausente, inválida, revogada ou expirada. \`{"detail": "Invalid or missing API key"}\`
- \`403\`: o papel da chave não pode criar. \`{"detail": "This API key's role cannot create vulnerabilities"}\`
- \`413\`: corpo acima de 1 MB.
- \`422\`: dados inválidos. Exemplos:

\`\`\`
{"detail": "Required for status 'saved_local': description, finding_detail, mitigation"}
{"detail": "unknown operator(s): nobody; operator(s) not active writers: isabella"}
{"detail": [{"loc": ["body", "cvss_score"], "msg": "Input should be less than or equal to 10", ...}]}
\`\`\`

### Boas práticas

- Uma chave por ferramenta, com papel *Editor (todos)* e data de expiração. Revogue as que não forem mais usadas.
- Nunca coloque a chave no código ou em repositórios: leia de uma variável de ambiente ou de um cofre.
- **Não há deduplicação:** repetir a mesma requisição cria outro registro. Depois de um erro de rede, confira no portal (filtro \`source:\`) antes de reenviar.
- Envie como \`draft\` quando um analista ainda precisa revisar o achado.`,
  },
  {
    id: 'admin', title: 'Administração', roles: ['admin'],
    md: `- **Usuários:** busque, filtre, crie usuários e altere papéis. Na ficha de cada usuário você vê a quais vulnerabilidades e relatórios ele tem acesso e por quê (criou, é operador, compartilhado, via relatório). *Redefinir senha* obriga o usuário a trocá-la no próximo acesso. *Desativar* bloqueia o acesso imediatamente.
- **Chaves de API:** para ferramentas que enviam vulnerabilidades automaticamente. A chave aparece **uma única vez** ao ser criada; depois, só o prefixo. Revogue chaves que não forem mais usadas.
- **Templates:** a página mostra quantos aguardam aprovação; abra cada um para aprovar ou recusar.
- **Reservas de relatório:** você pode liberar a reserva de edição de outra pessoa (fica registrado na auditoria).`,
  },
  {
    id: 'auditoria', title: 'Logs de auditoria', roles: ['admin', 'auditor'],
    md: `Os **Logs de Auditoria** registram logins, criações, alterações, mudanças de status, disparos, exportações, leituras de anexos e liberações de reserva, com quem fez, quando e de qual IP. Filtre pelo tipo de ação.`,
  },
]

const en = [
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
    id: 'vulnerabilidades', title: 'Vulnerabilities',
    md: `**Create:** menu ➝ *Create Vulnerability*. Identifier, Description, Finding Details and Mitigation are required to send it. You are the default operator; use **+** to add operators or people in *Shared with*. Click a name to remove it.

**Lifecycle:**

1. **Draft:** being written. *Save draft* keeps it without full validation.
2. **Saved:** complete and ready (*Send*).
3. **Dispatched:** delivered (*Dispatch*). Its content is now closed for editing.
4. **Acknowledged:** once the RVS ID is recorded in the *RVS Queue*.
5. **Waiting fix ➝ Retest pending ➝ Fixed:** follow-up of the fix. A failed retest goes back to *Waiting fix*.

After dispatch only operators and internal notes stay editable. If a status was changed by mistake, an administrator can use **Correct status**, which is recorded in the audit log.

If someone else saved the same vulnerability while you were editing, the portal tells you and shows the latest version instead of overwriting their work.`,
  },
  {
    id: 'rvs', title: 'RVS Queue',
    md: `The **RVS Queue** lists dispatched vulnerabilities that have no RVS ID yet. Enter the ID (e.g. \`RVS-2026-001\`) to mark the vulnerability **Acknowledged**. The ID can't be changed afterwards.`,
  },
  {
    id: 'relatorios', title: 'Reports',
    md: `**Create:** menu ➝ Reports ➝ *Create Report*. Optionally pick a **template** to start from ready-made text.

**Edit:** click **Edit** to reserve the report. While you edit, nobody else can change it; the reservation is released when you leave or after **10 minutes** without activity. If someone else holds it, the portal shows who. An administrator can release it.

**Content:** General Information, Report Data, Executive Summary, Introduction, Additional Sections (with their own titles, reorderable), the report's vulnerabilities, evidence and internal notes. Outside editing, the page shows the content as it reads in the report.

**Dispatch:** delivers the report with its vulnerabilities. If delivery fails, the report says so and can be dispatched again. Only **Draft** reports can be deleted.

**Save as Template:** keeps the current Executive Summary, Introduction and Additional Sections as a template of yours.`,
  },
  {
    id: 'templates', title: 'Templates', roles: CREATORS,
    md: `Templates are ready-made text (Executive Summary, Introduction and Additional Sections) to start reports from. They live in menu ➝ Reports ➝ *Templates*.

- A new template is **Private**: only you see and use it, and you can edit or delete it.
- **Request sharing** sends it for approval (**Awaiting approval**). From then on you can't change it; *Cancel request* makes it private again.
- An administrator **approves** it (**Shared**, available to everyone) or **rejects** it (back to private).
- Once shared, only administrators change it. To change something, create a new one from a report.
- An administrator can **unshare** it (**Unavailable**: nobody uses it, its author included) and **share it again** later.

A report copies the template's text when it is created; later changes to the template don't touch existing reports.`,
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
    id: 'api', title: 'Integration API', roles: CREATORS,
    md: `The API lets tools (scanners, C2s, recon pipelines) **create vulnerabilities** in the portal without the interface. It is separate from the API the portal itself uses: an API key works **only** on the \`/api/ingest/*\` endpoints.

### Endpoints

- \`POST /api/ingest/vulnerabilities\`: creates a vulnerability (as *Draft* or *Saved*). Needs an API key.
- \`GET /api/health\`: checks the portal is up. No key needed. Response: \`{"status": "ok", ...}\`.

### Keys and roles

Only an **administrator** creates keys, under *API Keys*. Ask one, saying which tool it is for. The key is shown **only once**, when created: keep it in a secrets vault. The portal stores only a hash and the prefix (8 characters) to identify it.

Each key has a **role**, which limits what it can do:

- **Editor (all)** or **Administrator**: can create vulnerabilities. Prefer *Editor (all)*, the least needed.
- **Reader (all)** or **Auditor**: create nothing (\`403\`). There are no read endpoints for keys yet.
- Whatever its role, a key does **not** reach users, reports, keys or the audit log: outside \`/api/ingest/*\` the answer is \`401\`.
- A key can have an **expiry date** and can be **revoked** at any time. A missing, unknown, revoked or expired key always gets the same \`401\`.
- The vulnerability created belongs to the administrator who issued the key. In the **Audit Logs**, the actor shows as \`api:<key prefix>\`.

### Authentication

Send the key in the \`X-API-Key\` header, with a JSON body:

\`\`\`
X-API-Key: <your key>
Content-Type: application/json
\`\`\`

### POST /api/ingest/vulnerabilities

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

\`id\` identifies the vulnerability (\`/vulnerabilities/<id>\` in the portal). \`internal_id\` is the \`VULN-xxxx\` number, present only when the status is \`saved_local\`.

### Examples

A draft from a scanner (the unknown \`host\` field goes to the metadata):

\`\`\`
curl -sS -X POST https://<portal>/api/ingest/vulnerabilities \\
  -H "X-API-Key: $PORTAL_KEY" -H "Content-Type: application/json" \\
  -d '{
        "identifier": "Exposed .git directory",
        "source": "nuclei",
        "cwe": "527",
        "cvss_score": 5.3,
        "references": ["https://cwe.mitre.org/data/definitions/527.html"],
        "operators": ["jonathan"],
        "host": "app.example.com"
      }'
# 201 {"id":"…","internal_id":null,"status":"draft"}
\`\`\`

A complete vulnerability, already **Saved**:

\`\`\`
curl -sS -X POST https://<portal>/api/ingest/vulnerabilities \\
  -H "X-API-Key: $PORTAL_KEY" -H "Content-Type: application/json" \\
  -d '{
        "status": "saved_local",
        "identifier": "SQL injection on /login",
        "description": "The **user** parameter is concatenated into the query.",
        "finding_detail": "Payload: 1 OR 1=1",
        "mitigation": "Use parameterised queries.",
        "cvss_score": 9.8,
        "source": "burp"
      }'
# 201 {"id":"…","internal_id":"VULN-0533","status":"saved_local"}
\`\`\`

Python:

\`\`\`
import os, requests

resp = requests.post(
    "https://<portal>/api/ingest/vulnerabilities",
    headers={"X-API-Key": os.environ["PORTAL_KEY"]},
    json={"identifier": "Open redirect", "source": "custom-scanner",
          "metadata": {"scan_id": "2026-10-25-01"}},
    timeout=30,
)
resp.raise_for_status()
print(resp.json()["id"])
\`\`\`

### Errors

The error body always has \`detail\`: a text or, for format errors, a list with the field and the reason.

- \`401\`: missing, invalid, revoked or expired key. \`{"detail": "Invalid or missing API key"}\`
- \`403\`: the key's role cannot create. \`{"detail": "This API key's role cannot create vulnerabilities"}\`
- \`413\`: body over 1 MB.
- \`422\`: invalid data. Examples:

\`\`\`
{"detail": "Required for status 'saved_local': description, finding_detail, mitigation"}
{"detail": "unknown operator(s): nobody; operator(s) not active writers: isabella"}
{"detail": [{"loc": ["body", "cvss_score"], "msg": "Input should be less than or equal to 10", ...}]}
\`\`\`

### Good practice

- One key per tool, with role *Editor (all)* and an expiry date. Revoke keys no longer in use.
- Never put the key in code or repositories: read it from an environment variable or a vault.
- **There is no de-duplication:** repeating a request creates another record. After a network error, check the portal (\`source:\` filter) before sending again.
- Send as \`draft\` when an analyst still needs to review the finding.`,
  },
  {
    id: 'admin', title: 'Administration', roles: ['admin'],
    md: `- **Users:** search, filter, create users and change roles. Each user's panel shows which vulnerabilities and reports they can reach and why (created, operator, shared, through a report). *Reset password* makes the user change it at the next sign-in. *Deactivate* blocks access at once.
- **API keys:** for tools that send vulnerabilities automatically. A key is shown **only once**, when created; afterwards only its prefix. Revoke keys no longer in use.
- **Templates:** the page shows how many await approval; open each one to approve or reject it.
- **Report reservations:** you can release someone else's editing reservation (recorded in the audit log).`,
  },
  {
    id: 'auditoria', title: 'Audit logs', roles: ['admin', 'auditor'],
    md: `The **Audit Logs** record sign-ins, creations, changes, status changes, dispatches, exports, attachment reads and reservation releases, with who did it, when and from which IP. Filter by type of action.`,
  },
]

export const DOCS = { 'pt-BR': pt, en }
