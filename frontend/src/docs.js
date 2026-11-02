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
        id: 'identificadores', title: 'Identificadores',
        md: `Cada registro tem até três identificações na tela:

- **Identificador:** o nome da vulnerabilidade ou do relatório, escrito por quem o cria. É como o registro aparece nas listas e títulos. Pode ser alterado enquanto o conteúdo estiver aberto para edição.
- **ID interno:** o número gerado pelo portal (\`VULN-0012\`, \`OP-0003\`). Vulnerabilidades o recebem ao *Concluir*; relatórios e suas vulnerabilidades, ao *Enviar*. Antes disso, o registro não tem ID interno. Depois de atribuído, não muda.
- **RVS:** o ID definido pelo Blue Team, registrado depois do envio. Existe só em vulnerabilidades, não em relatórios, e não muda depois de registrado.`,
      },
      {
        id: 'operacoes', title: 'Operações e filtros',
        md: `A página **Operações** lista vulnerabilidades e relatórios. Clique em uma linha para ver o resumo; abra o registro para os detalhes. Marque várias linhas para ações em lote (exportar, enviar, excluir). Itens que não podem receber a ação são ignorados e informados.

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
        md: `Os **Logs de Auditoria** registram logins, criações, alterações, mudanças de status, envios, exportações, leituras de anexos e liberações de reserva, com quem fez, quando e de qual IP. Filtre pelo tipo de ação.`,
      },
    ],
  },
  {
    id: 'vulnerabilidades', title: 'Vulnerabilidades',
    subs: [
      {
        id: 'vuln-criar', title: 'Criar uma vulnerabilidade',
        md: `Menu ➝ *Criar Vulnerabilidade*. Identificador, Descrição, Detalhes do Achado e Mitigação são obrigatórios para concluir. Você é o operador padrão; use **+** para adicionar outros operadores ou pessoas em *Compartilhado com*. Clique em um nome para removê-lo.`,
      },
      {
        id: 'vuln-ciclo', title: 'Ciclo de vida',
        md: `1. **Rascunho:** em edição. *Salvar rascunho* guarda sem validar tudo. *Concluir* exige os campos obrigatórios e atribui o ID interno \`VULN-xxxx\`.
2. **Pronta:** completa, ainda não enviada. *Enviar* entrega ao time responsável.
3. **Enviada:** entregue e aguardando o ID de RVS. O conteúdo passa a ficar fechado para edição. *Registrar RVS* (na *Fila RVS*) inicia a correção.
4. **Em correção:** o time responsável está corrigindo. *Solicitar reteste* pede a verificação do Red Team.
5. **Em reteste:** o Red Team verifica a correção. *Aprovar reteste* conclui; *Reprovar reteste* volta para *Em correção*.
6. **Corrigida:** correção confirmada; fim do fluxo.`,
      },
      {
        id: 'vuln-apos', title: 'Depois do envio',
        md: `Depois do envio, apenas operadores e notas internas continuam editáveis. Se um status foi alterado por engano, um administrador pode usar **Ajustar status**, que fica registrado na auditoria.`,
      },
      {
        id: 'vuln-conflitos', title: 'Edições simultâneas',
        md: `Se outra pessoa salvou a mesma vulnerabilidade enquanto você editava, o portal avisa e mostra a versão mais recente, sem sobrescrever o trabalho dela.`,
      },
      {
        id: 'rvs', title: 'Fila RVS',
        md: `A **Fila RVS** lista as vulnerabilidades enviadas que ainda não têm ID de RVS. Informe o ID (ex.: \`RVS-2026-001\`) e use **Registrar RVS**: a vulnerabilidade passa para **Em correção**. O ID não pode ser alterado depois.`,
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
        id: 'rel-envio', title: 'Envio, progresso e exclusão',
        md: `O relatório tem dois status: **Rascunho** e **Enviado**. **Enviar** dá ao relatório seu ID interno (\`OP-xxxx\`) e o entrega com suas vulnerabilidades, que recebem seus IDs internos, ficam **Enviadas** e seguem o fluxo normal.

Se a entrega falhar, o relatório continua em **Rascunho**, bloqueado para edição, com o aviso *Falha no envio* e o botão **Tentar novamente**.

Depois do envio, o portal mostra o progresso, por exemplo *2 de 5 corrigidas*. Quando todas estiverem corrigidas, o relatório aparece como **Concluído**; isso é calculado, ninguém precisa marcar.

Só relatórios em **Rascunho** podem ser excluídos.`,
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
        id: 'api-visao', title: 'Visão geral',
        md: `A API permite que outros sistemas **leiam** vulnerabilidades e relatórios, **baixem** evidências e exportações, **registrem IDs de RVS** e **criem** vulnerabilidades. Ela é separada da API usada pelo próprio portal: uma chave de API **só** funciona em \`/api/v1/*\`.

Endpoints (cada um tem uma subseção abaixo, com parâmetros, resposta, erros e exemplo):

- \`GET /api/v1/vulnerabilities\`: listar vulnerabilidades. \`vulns:read\`
- \`GET /api/v1/vulnerabilities/{ref}\`: ler uma vulnerabilidade. \`vulns:read\`
- \`GET /api/v1/vulnerabilities/{ref}/attachments\`: evidências dela. \`vulns:read\`
- \`GET /api/v1/attachments/{id}/content\`: baixar uma evidência. \`vulns:read\` ou \`reports:read\`
- \`GET /api/v1/vulnerabilities/{ref}/export\`: exportar (PDF, Word). \`exports\`
- \`GET /api/v1/rvs-queue\`: Fila RVS. \`rvs:write\` ou \`vulns:read\`
- \`POST /api/v1/vulnerabilities/{ref}/rvs\`: registrar o ID de RVS. \`rvs:write\`
- \`POST /api/v1/vulnerabilities\`: criar uma vulnerabilidade. \`vulns:write\`
- \`GET /api/v1/reports\`: listar relatórios. \`reports:read\`
- \`GET /api/v1/reports/{ref}\`: ler um relatório. \`reports:read\`
- \`GET /api/v1/reports/{ref}/export\`: exportar (PDF, Excel, Word). \`exports\`
- \`GET /api/health\`: verificar o portal. Sem chave.`,
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
- Fora de \`/api/v1/*\`, nenhuma chave funciona (\`401\`), qualquer que seja o escopo.
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
        id: 'api-convencoes', title: 'Convenções: referências, paginação e sincronização',
        md: `\`{ref}\` aceita o UUID ou o ID interno (\`VULN-0012\`, \`OP-0003\`), sem diferenciar maiúsculas. Respostas e corpos são JSON em UTF-8.

As listas (\`/vulnerabilities\` e \`/reports\`) vêm em ordem de **última alteração** e em páginas:

\`\`\`
{"items": [ ... ], "next_cursor": "MjAyNi0xMC0wOF..."}
\`\`\`

- \`limit\`: itens por página, de 1 a 200 (padrão 50).
- \`cursor\`: passe o \`next_cursor\` recebido para obter a próxima página. \`null\` indica o fim.
- \`updated_since\`: só o que foi criado ou alterado a partir desse momento (ISO 8601, ex. \`2026-10-25T14:00:00Z\`).

Filtros de \`/vulnerabilities\`: \`status\` (repita para vários: \`status=sent&status=fixing\`), \`source\` (contém), \`report\` (UUID, número ou \`none\` para as que não estão em relatório) e \`cvss_min\`. Filtros de \`/reports\`: \`status\` e \`client\` (contém).

**Para sincronizar** outro sistema: guarde o \`updated_at\` do último item processado e, na próxima execução, peça \`updated_since\` com esse valor, seguindo \`next_cursor\` até o fim. Um item alterado de novo volta a aparecer.

- As listas trazem um **resumo**; busque \`/{ref}\` para o conteúdo completo.
- Datas e horas estão em **UTC**.
- **Notas internas** nunca saem pela API, assim como nas exportações.

Exemplo de sincronização (Python):

\`\`\`
import os, requests

API = "https://<portal>/api/v1"
H = {"X-API-Key": os.environ["PORTAL_KEY"]}

def changed_since(since):
    params = {"updated_since": since, "limit": 200}
    while True:
        page = requests.get(f"{API}/vulnerabilities", headers=H, params=params, timeout=30)
        page.raise_for_status()
        page = page.json()
        yield from page["items"]
        if not page["next_cursor"]:
            break
        params["cursor"] = page["next_cursor"]

for v in changed_since("2026-10-25T00:00:00Z"):
    print(v["internal_id"], v["status"], v["updated_at"])
\`\`\``,
      },
      {
        id: 'api-ep-vulns', title: 'Listar vulnerabilidades',
        md: `**\`GET /api/v1/vulnerabilities\`** · escopo \`vulns:read\`

Lista vulnerabilidades (não excluídas) em ordem de última alteração, em páginas.

**Parâmetros** (query)

- \`status\`: um ou mais status; repita o parâmetro para vários (\`status=sent&status=fixing\`).
- \`source\`: a fonte contém o texto (sem diferenciar maiúsculas).
- \`report\`: UUID ou número do relatório; \`none\` para as que não estão em relatório.
- \`cvss_min\`: CVSS maior ou igual (0 a 10).
- \`updated_since\`: só as criadas ou alteradas a partir desse momento (ISO 8601).
- \`limit\`: 1 a 200 (padrão 50); \`cursor\`: o \`next_cursor\` da página anterior.

**Resposta \`200\`**: \`{"items": [...], "next_cursor": "…" | null}\`. Cada item tem:

- \`id\` (UUID) e \`internal_id\` (\`VULN-xxxx\`, nulo enquanto for rascunho).
- \`status\`: \`draft\`, \`ready\`, \`sent\`, \`fixing\`, \`retesting\` ou \`fixed\`.
- \`identifier\`, \`cwe\`, \`cvss_score\` (número ou nulo), \`source\`, \`rvs_id\` (nulo até o registro de RVS).
- \`report\`: \`{id, internal_id, name, status}\` do relatório a que pertence, ou nulo.
- \`created_at\`, \`updated_at\` (UTC).

**Erros**: \`422\` para status, data ou cursor inválidos; \`404\` se o relatório de \`report\` não existir.

**Exemplo**

\`\`\`
curl -sS "https://<portal>/api/v1/vulnerabilities?status=fixing&limit=1" \\
  -H "X-API-Key: $PORTAL_KEY"
\`\`\`

\`\`\`
{
  "items": [
    {
      "id": "92157428-3168-4c4e-9031-569928030ee9",
      "internal_id": "VULN-0003",
      "status": "fixing",
      "identifier": "Cross-Site Scripting (armazenado) - bi",
      "cwe": "CWE-79",
      "cvss_score": 10,
      "source": "nuclei",
      "rvs_id": "RVS-2026-1005",
      "report": null,
      "created_at": "2026-10-08T12:59:30.258918",
      "updated_at": "2026-10-08T12:59:30.315866"
    }
  ],
  "next_cursor": "MjAyNi0xMC0wOFQxMjo1OTozMC4zMTU4NjZ8OTIxNTc0Mjgt…"
}
\`\`\``,
      },
      {
        id: 'api-ep-vuln', title: 'Ler uma vulnerabilidade',
        md: `**\`GET /api/v1/vulnerabilities/{ref}\`** · escopo \`vulns:read\`

Uma vulnerabilidade completa.

**Parâmetros**: \`ref\` (caminho): UUID ou número (\`VULN-0003\`).

**Resposta \`200\`**: os campos do resumo (ver *Listar vulnerabilidades*) e também:

- \`description\`, \`finding_detail\`, \`mitigation\`: textos em Markdown.
- \`references\` (lista de URLs), \`cvss_vector\`.
- \`operators\`: logins dos operadores.
- \`metadata\`: dados livres enviados pela ferramenta que a criou.
- \`ready_at\`, \`sent_at\`, \`fixing_at\`, \`retesting_at\`, \`fixed_at\`: quando entrou em cada status (UTC), ou nulo.

Notas internas e a lista *Compartilhado com* não são enviadas.

**Erros**: \`404\` \`{"detail": "Vulnerability not found"}\`.

**Exemplo**

\`\`\`
curl -sS https://<portal>/api/v1/vulnerabilities/VULN-0003 -H "X-API-Key: $PORTAL_KEY"
\`\`\`

\`\`\`
{
  "id": "92157428-3168-4c4e-9031-569928030ee9",
  "internal_id": "VULN-0003",
  "status": "fixing",
  "identifier": "Cross-Site Scripting (armazenado) - bi",
  "cwe": "CWE-79",
  "cvss_score": 10,
  "source": "nuclei",
  "rvs_id": "RVS-2026-1005",
  "report": null,
  "created_at": "2026-10-08T12:59:30.258918",
  "updated_at": "2026-10-08T12:59:30.315866",
  "description": "Conteúdo persistido e renderizado sem escape.",
  "finding_detail": "Identificado em bi. Reprodução: requisição ao endpoint /bi/v2/recurso/…",
  "mitigation": "Sanitizar na entrada e escapar na saída.",
  "references": [],
  "cvss_vector": "AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:N",
  "operators": [
    "benjamin",
    "michelle"
  ],
  "metadata": {},
  "ready_at": "2026-10-08T12:59:30.282810",
  "sent_at": "2026-10-08T12:59:30.301332",
  "fixing_at": "2026-10-08T12:59:30.319272",
  "retesting_at": null,
  "fixed_at": null
}
\`\`\``,
      },
      {
        id: 'api-ep-vuln-atts', title: 'Evidências de uma vulnerabilidade',
        md: `**\`GET /api/v1/vulnerabilities/{ref}/attachments\`** · escopo \`vulns:read\`

Os arquivos anexados à vulnerabilidade, do mais antigo ao mais novo. Use o \`id\` para baixar cada um.

**Parâmetros**: \`ref\` (caminho).

**Resposta \`200\`**: lista de \`{id, filename, display_name, mime_type, size_bytes, created_at}\`.

**Erros**: \`404\`.

**Exemplo**

\`\`\`
curl -sS https://<portal>/api/v1/vulnerabilities/VULN-0012/attachments -H "X-API-Key: $PORTAL_KEY"
\`\`\`

\`\`\`
[
  {
    "id": "3f1c2a9e-5b7d-4e61-9a0c-2d8e4b6f1a73",
    "filename": "login-burp.png",
    "display_name": "Requisição de login",
    "mime_type": "image/png",
    "size_bytes": 48213,
    "created_at": "2026-10-20T14:02:11.502114"
  }
]
\`\`\``,
      },
      {
        id: 'api-ep-att', title: 'Baixar uma evidência',
        md: `**\`GET /api/v1/attachments/{id}/content\`** · escopo \`vulns:read\` ou \`reports:read\`

O conteúdo do arquivo, com o \`Content-Type\` dele e \`Content-Disposition: attachment\`. A evidência de uma vulnerabilidade exige \`vulns:read\`; a de um relatório, \`reports:read\`. Cada download fica registrado na auditoria.

**Parâmetros**: \`id\` (caminho): o \`id\` da evidência.

**Resposta \`200\`**: o arquivo (binário).

**Erros**: \`404\` se o arquivo não existir ou se a chave não tiver o escopo do dono dele.

**Exemplo**

\`\`\`
curl -sS -o login-burp.png https://<portal>/api/v1/attachments/3f1c2a9e-5b7d-4e61-9a0c-2d8e4b6f1a73/content \\
  -H "X-API-Key: $PORTAL_KEY"
\`\`\``,
      },
      {
        id: 'api-ep-vuln-export', title: 'Exportar uma vulnerabilidade',
        md: `**\`GET /api/v1/vulnerabilities/{ref}/export\`** · escopo \`exports\`

O mesmo arquivo do botão *Exportar*, com as imagens de evidência. Fica registrado na auditoria.

**Parâmetros**: \`ref\` (caminho); \`format\` (query): \`pdf\` (padrão) ou \`docx\`.

**Resposta \`200\`**: o arquivo, com \`Content-Disposition: attachment; filename*=UTF-8''VULN-0002.docx\`.

**Erros**: \`404\`; \`422\` para outro formato.

**Exemplo**

\`\`\`
curl -sS -o VULN-0002.pdf "https://<portal>/api/v1/vulnerabilities/VULN-0002/export?format=pdf" \\
  -H "X-API-Key: $PORTAL_KEY"
\`\`\``,
      },
      {
        id: 'api-ep-rvsq', title: 'Fila RVS',
        md: `**\`GET /api/v1/rvs-queue\`** · escopo \`rvs:write\` ou \`vulns:read\`

Vulnerabilidades **enviadas** que ainda não têm ID de RVS, da enviada há mais tempo para a mais recente. Sem paginação.

**Parâmetros**: Nenhum.

**Resposta \`200\`**: lista de resumos (mesmos campos de *Listar vulnerabilidades*).

**Exemplo**

\`\`\`
curl -sS https://<portal>/api/v1/rvs-queue -H "X-API-Key: $PORTAL_KEY"
\`\`\`

\`\`\`
[
  {
    "id": "6598c3c4-c1eb-43d3-8412-3c36d1682462",
    "internal_id": "VULN-0001",
    "status": "sent",
    "identifier": "Deserialização insegura - erp",
    "cwe": "CWE-502",
    "cvss_score": 3.3,
    "source": "nessus",
    "rvs_id": null,
    "report": null,
    "created_at": "2026-10-08T12:59:30.068791",
    "updated_at": "2026-10-08T12:59:30.108013"
  }
]
\`\`\``,
      },
      {
        id: 'api-ep-rvs', title: 'Registrar o ID de RVS',
        md: `**\`POST /api/v1/vulnerabilities/{ref}/rvs\`** · escopo \`rvs:write\`

Registra o ID de RVS de uma vulnerabilidade enviada, que passa para **Em correção**. O ID não pode ser alterado depois. Fica registrado na auditoria.

**Parâmetros**: \`ref\` (caminho).

**Corpo** (JSON): \`{"rvs_id": "RVS-2026-001"}\`: texto de 1 a 200 caracteres.

**Resposta \`200\`**: a vulnerabilidade completa (como em *Ler uma vulnerabilidade*), com \`status: "fixing"\` e o \`rvs_id\`.

**Erros**

- \`409\` se não estiver enviada: \`{"detail": "RVS ID can only be set on a sent vuln (current: fixing)"}\`
- \`409\` se o ID já foi registrado: \`{"detail": "RVS ID is already set"}\`
- \`404\`; \`422\` para \`rvs_id\` vazio.

**Exemplo**

\`\`\`
curl -sS -X POST https://<portal>/api/v1/vulnerabilities/VULN-0001/rvs \\
  -H "X-API-Key: $PORTAL_KEY" -H "Content-Type: application/json" \\
  -d '{"rvs_id": "RVS-2026-001"}'
\`\`\`

\`\`\`
{
  "id": "6598c3c4-c1eb-43d3-8412-3c36d1682462",
  "internal_id": "VULN-0001",
  "status": "fixing",
  "rvs_id": "RVS-2026-001",
  "fixing_at": "2026-10-25T16:30:02.118204",
  "…": "demais campos de Ler uma vulnerabilidade"
}
\`\`\``,
      },
      {
        id: 'api-criar', title: 'Criar uma vulnerabilidade',
        md: `**\`POST /api/v1/vulnerabilities\`** · escopo \`vulns:write\`

Corpo JSON de até **1 MB**. Todos os campos são opcionais, respeitando as regras abaixo:

- \`identifier\` (texto, até 500): CVE ou nome do achado.
- \`description\`, \`finding_detail\`, \`mitigation\` (Markdown, até 100.000 cada): Descrição, Detalhes do Achado e Mitigação.
- \`cwe\` (texto): \`CWE-79\` ou só \`79\`; é normalizado para \`CWE-79\`.
- \`cvss_score\` (número de 0 a 10) e \`cvss_vector\` (texto, até 200).
- \`references\` (lista de até 50 URLs): cada uma precisa começar com \`http://\` ou \`https://\`.
- \`source\` (texto, até 200): a ferramenta de origem, ex. \`nuclei\`, \`burp\`. Aparece em *Fontes* e no filtro \`source:\`.
- \`internal_notes\` (Markdown): notas internas.
- \`operators\` (lista de até 20 **logins**): usuários **ativos** com papel Administrador, Editor (todos) ou Editor restrito.
- \`status\`: \`"draft"\` (padrão) ou \`"ready"\`. A API nunca cria vulnerabilidades enviadas.
- \`metadata\` (objeto): dados livres da ferramenta, guardados como vieram. **Campos desconhecidos** no corpo também vão para os metadados. Limite: 64 KB no total.

Regras:

- Pelo menos um entre \`identifier\`, \`description\` e \`finding_detail\` deve ser preenchido.
- \`"ready"\` exige \`identifier\`, \`description\`, \`finding_detail\` e \`mitigation\` (os mesmos campos do botão *Concluir*) e já atribui o ID interno \`VULN-xxxx\`.

Resposta \`201\`:

\`\`\`
{"id": "72643b23-af52-42d9-a139-c1aea6f70a15", "internal_id": null, "status": "draft"}
\`\`\`

\`id\` identifica a vulnerabilidade (\`/vulnerabilities/<id>\` no portal). \`internal_id\` é o ID interno \`VULN-xxxx\`, presente apenas quando o status é \`ready\`.

**Exemplo**

\`\`\`
curl -sS -X POST https://<portal>/api/v1/vulnerabilities \\
  -H "X-API-Key: $PORTAL_KEY" -H "Content-Type: application/json" \\
  -d '{"identifier": "Exposed .git directory", "source": "nuclei", "cwe": "527",
       "cvss_score": 5.3, "operators": ["jonathan"], "host": "app.example.com"}'
\`\`\`

\`\`\`
201
{
  "id": "72643b23-af52-42d9-a139-c1aea6f70a15",
  "internal_id": null,
  "status": "draft"
}
\`\`\``,
      },
      {
        id: 'api-ep-reports', title: 'Listar relatórios',
        md: `**\`GET /api/v1/reports\`** · escopo \`reports:read\`

Lista relatórios (não excluídos) em ordem de última alteração, em páginas.

**Parâmetros** (query)

- \`status\`: \`draft\` ou \`sent\`; repita para vários.
- \`client\`: o nome do cliente contém o texto.
- \`updated_since\`, \`limit\`, \`cursor\`: como em *Listar vulnerabilidades*.

**Resposta \`200\`**: \`{"items": [...], "next_cursor": …}\`. Cada item tem \`id\`, \`internal_id\` (\`OP-xxxx\`, nulo até o envio), \`name\`, \`client_name\`, \`status\`, \`start_date\`, \`end_date\` (datas \`AAAA-MM-DD\`), \`sent_at\`, \`vulnerability_count\`, \`fixed_count\`, \`created_at\`, \`updated_at\`.

**Exemplo**

\`\`\`
curl -sS "https://<portal>/api/v1/reports?status=sent&limit=1" -H "X-API-Key: $PORTAL_KEY"
\`\`\`

\`\`\`
{
  "items": [
    {
      "id": "056c3eee-6d69-47c2-876a-f099dcbc45f9",
      "internal_id": "OP-0001",
      "name": "Pentest Aplicação Web - Portal do Cliente",
      "client_name": "Banco Aurora S.A.",
      "status": "sent",
      "start_date": "2026-08-03",
      "end_date": "2026-08-21",
      "sent_at": "2026-10-08T12:59:35.258463",
      "vulnerability_count": 3,
      "fixed_count": 0,
      "created_at": "2026-10-08T12:59:35.029437",
      "updated_at": "2026-10-08T12:59:35.204803"
    }
  ],
  "next_cursor": "MjAyNi0xMC0wOFQxMjo1OTozNS4yMDQ4MDN8MDU2YzNlZWUt…"
}
\`\`\``,
      },
      {
        id: 'api-ep-report', title: 'Ler um relatório',
        md: `**\`GET /api/v1/reports/{ref}\`** · escopo \`reports:read\`

Um relatório completo.

**Parâmetros**: \`ref\` (caminho): UUID ou número (\`OP-0001\`).

**Resposta \`200\`**: os campos do resumo e também:

- \`test_type\`, \`test_model\`, \`environment\`, \`demand_origin\`, \`scope\`.
- \`executive_summary_md\`, \`introduction_md\`: Markdown.
- \`sections\`: Seções Adicionais em ordem, \`{position, title, content_markdown}\`.
- \`operators\`: logins.
- \`vulnerabilities\`: resumos das vulnerabilidades do relatório.
- \`attachments\`: as evidências do relatório, como em *Evidências de uma vulnerabilidade*.

Notas internas não são enviadas.

**Erros**: \`404\` \`{"detail": "Report not found"}\`.

**Exemplo**

\`\`\`
curl -sS https://<portal>/api/v1/reports/OP-0001 -H "X-API-Key: $PORTAL_KEY"
\`\`\`

\`\`\`
{
  "id": "056c3eee-6d69-47c2-876a-f099dcbc45f9",
  "internal_id": "OP-0001",
  "name": "Pentest Aplicação Web - Portal do Cliente",
  "client_name": "Banco Aurora S.A.",
  "status": "sent",
  "start_date": "2026-08-03",
  "end_date": "2026-08-21",
  "sent_at": "2026-10-08T12:59:35.258463",
  "vulnerability_count": 3,
  "fixed_count": 0,
  "created_at": "2026-10-08T12:59:35.029437",
  "updated_at": "2026-10-08T12:59:35.204803",
  "test_type": "Pentest",
  "test_model": "Gray box",
  "environment": "Homologação",
  "demand_origin": "Contratação anual",
  "scope": "banco-aurora-s.a..example",
  "executive_summary_md": "Foram identificadas vulnerabilidades que exigem **atenção prioritária**…",
  "introduction_md": "Resultados do trabalho realizado para **Banco Aurora S.A.**.",
  "sections": [
    {
      "position": 1,
      "title": "Metodologia",
      "content_markdown": "Testes manuais e automatizados, seguindo OWASP e PTES."
    }
  ],
  "operators": [
    "jonathan"
  ],
  "vulnerabilities": [
    {
      "id": "e4a61965-ab90-41f6-b0d3-d05db0816f74",
      "internal_id": "VULN-0074",
      "status": "sent",
      "identifier": "Falta de rate limiting - intranet",
      "cwe": "CWE-770",
      "cvss_score": 8.1,
      "source": "manual",
      "rvs_id": null,
      "report": {
        "id": "056c3eee-6d69-47c2-876a-f099dcbc45f9",
        "internal_id": "OP-0001",
        "name": "Pentest Aplicação Web - Portal do Cliente",
        "status": "sent"
      },
      "created_at": "2026-10-08T12:59:35.119620",
      "updated_at": "2026-10-08T12:59:35.204803"
    }
  ],
  "attachments": []
}
\`\`\``,
      },
      {
        id: 'api-ep-report-export', title: 'Exportar um relatório',
        md: `**\`GET /api/v1/reports/{ref}/export\`** · escopo \`exports\`

Os mesmos arquivos do botão *Exportar*: o relatório em PDF ou Word, ou a planilha das vulnerabilidades em Excel. Fica registrado na auditoria.

**Parâmetros**: \`ref\` (caminho); \`format\` (query): \`pdf\` (padrão), \`xlsx\` ou \`docx\`.

**Resposta \`200\`**: o arquivo, com \`Content-Disposition\` (ex. \`OP-0001_20261025.pdf\`, \`OP-0001_vulnerabilidades_20261025.xlsx\`).

**Erros**: \`404\`; \`422\` para outro formato.

**Exemplo**

\`\`\`
curl -sS -o OP-0001.xlsx "https://<portal>/api/v1/reports/OP-0001/export?format=xlsx" \\
  -H "X-API-Key: $PORTAL_KEY"
\`\`\``,
      },
      {
        id: 'api-ep-health', title: 'Verificar o portal',
        md: `**\`GET /api/health\`** · sem chave

Responde \`200\` enquanto o portal está no ar. Útil para monitoração.

**Exemplo**

\`\`\`
curl -sS https://<portal>/api/health
\`\`\`

\`\`\`
{
  "status": "ok",
  "environment": "production"
}
\`\`\``,
      },
      {
        id: 'api-erros', title: 'Erros',
        md: `O corpo de erro sempre traz \`detail\`: um texto ou, em erros de formato, uma lista com o campo e o motivo.

- \`401\`: chave ausente, inválida, revogada ou expirada. \`{"detail": "Invalid or missing API key"}\`
- \`403\`: a chave não tem o escopo do endpoint. \`{"detail": "This API key lacks the scope 'rvs:write'"}\`
- \`404\`: o registro não existe (ou foi excluído).
- \`409\`: a ação não cabe no status atual, ex. RVS em vulnerabilidade não enviada ou já registrado.
- \`413\`: corpo acima de 1 MB.
- \`422\`: dados ou parâmetros inválidos (inclusive \`cursor\` inválido). Exemplos:

\`\`\`
{"detail": "Required for status 'ready': description, finding_detail, mitigation"}
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
        md: `Menu ➝ *Logs de Auditoria*. Registra logins, criações, alterações, mudanças de status, envios, exportações, leituras de anexos e liberações de reserva, com quem fez (usuário ou \`api:<prefixo>\` para chaves), quando e de qual IP. Filtre pelo tipo de ação.`,
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
        id: 'identificadores', title: 'Identifiers',
        md: `Each record has up to three identifications on screen:

- **Identifier:** the name of the vulnerability or report, written by whoever creates it. It is how the record shows in lists and titles. It can change while the content is open for editing.
- **Internal ID:** the number the portal generates (\`VULN-0012\`, \`OP-0003\`). Vulnerabilities get it on *Complete*; reports and their vulnerabilities, on *Send*. Until then the record has no internal ID. Once assigned, it never changes.
- **RVS:** the ID set by the Blue Team, recorded after sending. It exists only on vulnerabilities, not on reports, and doesn't change once recorded.`,
      },
      {
        id: 'operacoes', title: 'Operations and filters',
        md: `The **Operations** page lists vulnerabilities and reports. Click a row for a summary; open the record for its details. Tick several rows for batch actions (export, send, delete). Items the action doesn't apply to are skipped and reported.

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
        md: `The **Audit Logs** record sign-ins, creations, changes, status changes, sends, exports, attachment reads and reservation releases, with who did it, when and from which IP. Filter by type of action.`,
      },
    ],
  },
  {
    id: 'vulnerabilidades', title: 'Vulnerabilities',
    subs: [
      {
        id: 'vuln-criar', title: 'Create a vulnerability',
        md: `Menu ➝ *Create Vulnerability*. Identifier, Description, Finding Details and Mitigation are required to complete it. You are the default operator; use **+** to add operators or people in *Shared with*. Click a name to remove it.`,
      },
      {
        id: 'vuln-ciclo', title: 'Lifecycle',
        md: `1. **Draft:** being written. *Save draft* keeps it without full validation. *Complete* needs the required fields and assigns the \`VULN-xxxx\` internal ID.
2. **Ready:** complete, not sent yet. *Send* delivers it to the responsible team.
3. **Sent:** delivered, waiting for the RVS ID. Its content is now closed for editing. *Record RVS* (in the *RVS Queue*) starts the fix.
4. **Fixing:** the responsible team is fixing it. *Request retest* asks the Red Team to verify.
5. **Retesting:** the Red Team checks the fix. *Pass retest* finishes it; *Fail retest* goes back to *Fixing*.
6. **Fixed:** fix confirmed; end of the flow.`,
      },
      {
        id: 'vuln-apos', title: 'After sending',
        md: `After sending, only operators and internal notes stay editable. If a status was changed by mistake, an administrator can use **Adjust status**, which is recorded in the audit log.`,
      },
      {
        id: 'vuln-conflitos', title: 'Simultaneous edits',
        md: `If someone else saved the same vulnerability while you were editing, the portal tells you and shows the latest version instead of overwriting their work.`,
      },
      {
        id: 'rvs', title: 'RVS Queue',
        md: `The **RVS Queue** lists sent vulnerabilities that have no RVS ID yet. Enter the ID (e.g. \`RVS-2026-001\`) and use **Record RVS**: the vulnerability moves to **Fixing**. The ID can't be changed afterwards.`,
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
        id: 'rel-envio', title: 'Sending, progress and deletion',
        md: `A report has two statuses: **Draft** and **Sent**. **Send** gives the report its internal ID (\`OP-xxxx\`) and delivers it with its vulnerabilities, which get their internal IDs, become **Sent** and follow the normal flow.

If delivery fails, the report stays a **Draft**, locked for editing, with a *Sending failed* warning and a **Try again** button.

After sending, the portal shows the progress, for example *2 of 5 fixed*. When all are fixed, the report shows as **Completed**; this is worked out for you, nobody marks it.

Only **Draft** reports can be deleted.`,
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
        id: 'api-visao', title: 'Overview',
        md: `The API lets other systems **read** vulnerabilities and reports, **download** evidence and exports, **record RVS IDs** and **create** vulnerabilities. It is separate from the API the portal itself uses: an API key works **only** on \`/api/v1/*\`.

Endpoints (each has a subsection below, with parameters, response, errors and an example):

- \`GET /api/v1/vulnerabilities\`: list vulnerabilities. \`vulns:read\`
- \`GET /api/v1/vulnerabilities/{ref}\`: read a vulnerability. \`vulns:read\`
- \`GET /api/v1/vulnerabilities/{ref}/attachments\`: its evidence. \`vulns:read\`
- \`GET /api/v1/attachments/{id}/content\`: download evidence. \`vulns:read\` or \`reports:read\`
- \`GET /api/v1/vulnerabilities/{ref}/export\`: export (PDF, Word). \`exports\`
- \`GET /api/v1/rvs-queue\`: RVS queue. \`rvs:write\` or \`vulns:read\`
- \`POST /api/v1/vulnerabilities/{ref}/rvs\`: record the RVS ID. \`rvs:write\`
- \`POST /api/v1/vulnerabilities\`: create a vulnerability. \`vulns:write\`
- \`GET /api/v1/reports\`: list reports. \`reports:read\`
- \`GET /api/v1/reports/{ref}\`: read a report. \`reports:read\`
- \`GET /api/v1/reports/{ref}/export\`: export (PDF, Excel, Word). \`exports\`
- \`GET /api/health\`: health check. No key.`,
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
- Outside \`/api/v1/*\`, no key works (\`401\`), whatever its scopes.
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
        id: 'api-convencoes', title: 'Conventions: references, paging and syncing',
        md: `\`{ref}\` takes the UUID or the internal ID (\`VULN-0012\`, \`OP-0003\`), case-insensitive. Responses and bodies are UTF-8 JSON.

Lists (\`/vulnerabilities\` and \`/reports\`) come in **last-change** order and in pages:

\`\`\`
{"items": [ ... ], "next_cursor": "MjAyNi0xMC0wOF..."}
\`\`\`

- \`limit\`: items per page, 1 to 200 (default 50).
- \`cursor\`: pass the \`next_cursor\` you got to fetch the next page. \`null\` means the end.
- \`updated_since\`: only what was created or changed from that moment on (ISO 8601, e.g. \`2026-10-25T14:00:00Z\`).

\`/vulnerabilities\` filters: \`status\` (repeat for several: \`status=sent&status=fixing\`), \`source\` (contains), \`report\` (UUID, number, or \`none\` for those outside any report) and \`cvss_min\`. \`/reports\` filters: \`status\` and \`client\` (contains).

**To sync** another system: keep the \`updated_at\` of the last item you processed and, on the next run, ask for \`updated_since\` with that value, following \`next_cursor\` to the end. An item changed again shows up again.

- Lists carry a **summary**; fetch \`/{ref}\` for the full content.
- Dates and times are in **UTC**.
- **Internal notes** never leave through the API, as in the exports.

Sync example (Python):

\`\`\`
import os, requests

API = "https://<portal>/api/v1"
H = {"X-API-Key": os.environ["PORTAL_KEY"]}

def changed_since(since):
    params = {"updated_since": since, "limit": 200}
    while True:
        page = requests.get(f"{API}/vulnerabilities", headers=H, params=params, timeout=30)
        page.raise_for_status()
        page = page.json()
        yield from page["items"]
        if not page["next_cursor"]:
            break
        params["cursor"] = page["next_cursor"]

for v in changed_since("2026-10-25T00:00:00Z"):
    print(v["internal_id"], v["status"], v["updated_at"])
\`\`\``,
      },
      {
        id: 'api-ep-vulns', title: 'List vulnerabilities',
        md: `**\`GET /api/v1/vulnerabilities\`** · scope \`vulns:read\`

Lists (non-deleted) vulnerabilities in last-change order, in pages.

**Parameters** (query)

- \`status\`: one or more statuses; repeat the parameter for several (\`status=sent&status=fixing\`).
- \`source\`: the source contains the text (case-insensitive).
- \`report\`: report UUID or number; \`none\` for those outside any report.
- \`cvss_min\`: CVSS greater or equal (0 to 10).
- \`updated_since\`: only those created or changed from that moment on (ISO 8601).
- \`limit\`: 1 to 200 (default 50); \`cursor\`: the previous page's \`next_cursor\`.

**Response \`200\`**: \`{"items": [...], "next_cursor": "…" | null}\`. Each item has:

- \`id\` (UUID) and \`internal_id\` (\`VULN-xxxx\`, null while it is a draft).
- \`status\`: \`draft\`, \`ready\`, \`sent\`, \`fixing\`, \`retesting\` or \`fixed\`.
- \`identifier\`, \`cwe\`, \`cvss_score\` (number or null), \`source\`, \`rvs_id\` (null until the RVS ID is recorded).
- \`report\`: \`{id, internal_id, name, status}\` of the report it belongs to, or null.
- \`created_at\`, \`updated_at\` (UTC).

**Errors**: \`422\` for an invalid status, date or cursor; \`404\` if the \`report\` does not exist.

**Example**

\`\`\`
curl -sS "https://<portal>/api/v1/vulnerabilities?status=fixing&limit=1" \\
  -H "X-API-Key: $PORTAL_KEY"
\`\`\`

\`\`\`
{
  "items": [
    {
      "id": "92157428-3168-4c4e-9031-569928030ee9",
      "internal_id": "VULN-0003",
      "status": "fixing",
      "identifier": "Cross-Site Scripting (armazenado) - bi",
      "cwe": "CWE-79",
      "cvss_score": 10,
      "source": "nuclei",
      "rvs_id": "RVS-2026-1005",
      "report": null,
      "created_at": "2026-10-08T12:59:30.258918",
      "updated_at": "2026-10-08T12:59:30.315866"
    }
  ],
  "next_cursor": "MjAyNi0xMC0wOFQxMjo1OTozMC4zMTU4NjZ8OTIxNTc0Mjgt…"
}
\`\`\``,
      },
      {
        id: 'api-ep-vuln', title: 'Read a vulnerability',
        md: `**\`GET /api/v1/vulnerabilities/{ref}\`** · scope \`vulns:read\`

One complete vulnerability.

**Parameters**: \`ref\` (path): UUID or number (\`VULN-0003\`).

**Response \`200\`**: the summary fields (see *List vulnerabilities*) plus:

- \`description\`, \`finding_detail\`, \`mitigation\`: Markdown text.
- \`references\` (list of URLs), \`cvss_vector\`.
- \`operators\`: operator usernames.
- \`metadata\`: free data sent by the tool that created it.
- \`ready_at\`, \`sent_at\`, \`fixing_at\`, \`retesting_at\`, \`fixed_at\`: when it reached each status (UTC), or null.

Internal notes and the *Shared with* list are not sent.

**Errors**: \`404\` \`{"detail": "Vulnerability not found"}\`.

**Example**

\`\`\`
curl -sS https://<portal>/api/v1/vulnerabilities/VULN-0003 -H "X-API-Key: $PORTAL_KEY"
\`\`\`

\`\`\`
{
  "id": "92157428-3168-4c4e-9031-569928030ee9",
  "internal_id": "VULN-0003",
  "status": "fixing",
  "identifier": "Cross-Site Scripting (armazenado) - bi",
  "cwe": "CWE-79",
  "cvss_score": 10,
  "source": "nuclei",
  "rvs_id": "RVS-2026-1005",
  "report": null,
  "created_at": "2026-10-08T12:59:30.258918",
  "updated_at": "2026-10-08T12:59:30.315866",
  "description": "Conteúdo persistido e renderizado sem escape.",
  "finding_detail": "Identificado em bi. Reprodução: requisição ao endpoint /bi/v2/recurso/…",
  "mitigation": "Sanitizar na entrada e escapar na saída.",
  "references": [],
  "cvss_vector": "AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:N",
  "operators": [
    "benjamin",
    "michelle"
  ],
  "metadata": {},
  "ready_at": "2026-10-08T12:59:30.282810",
  "sent_at": "2026-10-08T12:59:30.301332",
  "fixing_at": "2026-10-08T12:59:30.319272",
  "retesting_at": null,
  "fixed_at": null
}
\`\`\``,
      },
      {
        id: 'api-ep-vuln-atts', title: 'A vulnerability\'s evidence',
        md: `**\`GET /api/v1/vulnerabilities/{ref}/attachments\`** · scope \`vulns:read\`

The files attached to the vulnerability, oldest first. Use the \`id\` to download each one.

**Parameters**: \`ref\` (path).

**Response \`200\`**: list of \`{id, filename, display_name, mime_type, size_bytes, created_at}\`.

**Errors**: \`404\`.

**Example**

\`\`\`
curl -sS https://<portal>/api/v1/vulnerabilities/VULN-0012/attachments -H "X-API-Key: $PORTAL_KEY"
\`\`\`

\`\`\`
[
  {
    "id": "3f1c2a9e-5b7d-4e61-9a0c-2d8e4b6f1a73",
    "filename": "login-burp.png",
    "display_name": "Requisição de login",
    "mime_type": "image/png",
    "size_bytes": 48213,
    "created_at": "2026-10-20T14:02:11.502114"
  }
]
\`\`\``,
      },
      {
        id: 'api-ep-att', title: 'Download evidence',
        md: `**\`GET /api/v1/attachments/{id}/content\`** · scope \`vulns:read\` or \`reports:read\`

The file's content, with its \`Content-Type\` and \`Content-Disposition: attachment\`. A vulnerability's evidence needs \`vulns:read\`; a report's, \`reports:read\`. Each download is recorded in the audit log.

**Parameters**: \`id\` (path): the evidence's \`id\`.

**Response \`200\`**: the file (binary).

**Errors**: \`404\` if the file does not exist or the key lacks its owner's scope.

**Example**

\`\`\`
curl -sS -o login-burp.png https://<portal>/api/v1/attachments/3f1c2a9e-5b7d-4e61-9a0c-2d8e4b6f1a73/content \\
  -H "X-API-Key: $PORTAL_KEY"
\`\`\``,
      },
      {
        id: 'api-ep-vuln-export', title: 'Export a vulnerability',
        md: `**\`GET /api/v1/vulnerabilities/{ref}/export\`** · scope \`exports\`

The same file as the *Export* button, with the evidence images. Recorded in the audit log.

**Parameters**: \`ref\` (path); \`format\` (query): \`pdf\` (default) or \`docx\`.

**Response \`200\`**: the file, with \`Content-Disposition: attachment; filename*=UTF-8''VULN-0002.docx\`.

**Errors**: \`404\`; \`422\` for another format.

**Example**

\`\`\`
curl -sS -o VULN-0002.pdf "https://<portal>/api/v1/vulnerabilities/VULN-0002/export?format=pdf" \\
  -H "X-API-Key: $PORTAL_KEY"
\`\`\``,
      },
      {
        id: 'api-ep-rvsq', title: 'RVS queue',
        md: `**\`GET /api/v1/rvs-queue\`** · scope \`rvs:write\` or \`vulns:read\`

**Sent** vulnerabilities that have no RVS ID yet, longest-waiting first. Not paginated.

**Parameters**: None.

**Response \`200\`**: list of summaries (same fields as *List vulnerabilities*).

**Example**

\`\`\`
curl -sS https://<portal>/api/v1/rvs-queue -H "X-API-Key: $PORTAL_KEY"
\`\`\`

\`\`\`
[
  {
    "id": "6598c3c4-c1eb-43d3-8412-3c36d1682462",
    "internal_id": "VULN-0001",
    "status": "sent",
    "identifier": "Deserialização insegura - erp",
    "cwe": "CWE-502",
    "cvss_score": 3.3,
    "source": "nessus",
    "rvs_id": null,
    "report": null,
    "created_at": "2026-10-08T12:59:30.068791",
    "updated_at": "2026-10-08T12:59:30.108013"
  }
]
\`\`\``,
      },
      {
        id: 'api-ep-rvs', title: 'Record the RVS ID',
        md: `**\`POST /api/v1/vulnerabilities/{ref}/rvs\`** · scope \`rvs:write\`

Records the RVS ID of a sent vulnerability, which moves to **Fixing**. The ID cannot be changed afterwards. Recorded in the audit log.

**Parameters**: \`ref\` (path).

**Body** (JSON): \`{"rvs_id": "RVS-2026-001"}\`: text, 1 to 200 characters.

**Response \`200\`**: the full vulnerability (as in *Read a vulnerability*), with \`status: "fixing"\` and the \`rvs_id\`.

**Errors**

- \`409\` if it is not sent: \`{"detail": "RVS ID can only be set on a sent vuln (current: fixing)"}\`
- \`409\` if the ID is already set: \`{"detail": "RVS ID is already set"}\`
- \`404\`; \`422\` for an empty \`rvs_id\`.

**Example**

\`\`\`
curl -sS -X POST https://<portal>/api/v1/vulnerabilities/VULN-0001/rvs \\
  -H "X-API-Key: $PORTAL_KEY" -H "Content-Type: application/json" \\
  -d '{"rvs_id": "RVS-2026-001"}'
\`\`\`

\`\`\`
{
  "id": "6598c3c4-c1eb-43d3-8412-3c36d1682462",
  "internal_id": "VULN-0001",
  "status": "fixing",
  "rvs_id": "RVS-2026-001",
  "fixing_at": "2026-10-25T16:30:02.118204",
  "…": "other fields as in Read a vulnerability"
}
\`\`\``,
      },
      {
        id: 'api-criar', title: 'Create a vulnerability',
        md: `**\`POST /api/v1/vulnerabilities\`** · scope \`vulns:write\`

JSON body of up to **1 MB**. Every field is optional, under the rules below:

- \`identifier\` (text, up to 500): CVE or name of the finding.
- \`description\`, \`finding_detail\`, \`mitigation\` (Markdown, up to 100,000 each): Description, Finding Details and Mitigation.
- \`cwe\` (text): \`CWE-79\` or just \`79\`; normalised to \`CWE-79\`.
- \`cvss_score\` (number 0 to 10) and \`cvss_vector\` (text, up to 200).
- \`references\` (list of up to 50 URLs): each must start with \`http://\` or \`https://\`.
- \`source\` (text, up to 200): the tool it came from, e.g. \`nuclei\`, \`burp\`. Shown in *Sources* and the \`source:\` filter.
- \`internal_notes\` (Markdown): internal notes.
- \`operators\` (list of up to 20 **usernames**): **active** users with role Administrator, Editor (all) or Restricted editor.
- \`status\`: \`"draft"\` (default) or \`"ready"\`. The API never creates sent vulnerabilities.
- \`metadata\` (object): free data from the tool, stored as sent. **Unknown fields** in the body go to the metadata too. Limit: 64 KB in total.

Rules:

- At least one of \`identifier\`, \`description\` and \`finding_detail\` must be filled in.
- \`"ready"\` needs \`identifier\`, \`description\`, \`finding_detail\` and \`mitigation\` (the same fields as the *Complete* button) and assigns the \`VULN-xxxx\` internal ID at once.

\`201\` response:

\`\`\`
{"id": "72643b23-af52-42d9-a139-c1aea6f70a15", "internal_id": null, "status": "draft"}
\`\`\`

\`id\` identifies the vulnerability (\`/vulnerabilities/<id>\` in the portal). \`internal_id\` is the \`VULN-xxxx\` internal ID, present only when the status is \`ready\`.

**Example**

\`\`\`
curl -sS -X POST https://<portal>/api/v1/vulnerabilities \\
  -H "X-API-Key: $PORTAL_KEY" -H "Content-Type: application/json" \\
  -d '{"identifier": "Exposed .git directory", "source": "nuclei", "cwe": "527",
       "cvss_score": 5.3, "operators": ["jonathan"], "host": "app.example.com"}'
\`\`\`

\`\`\`
201
{
  "id": "72643b23-af52-42d9-a139-c1aea6f70a15",
  "internal_id": null,
  "status": "draft"
}
\`\`\``,
      },
      {
        id: 'api-ep-reports', title: 'List reports',
        md: `**\`GET /api/v1/reports\`** · scope \`reports:read\`

Lists (non-deleted) reports in last-change order, in pages.

**Parameters** (query)

- \`status\`: \`draft\` or \`sent\`; repeat for several.
- \`client\`: the client name contains the text.
- \`updated_since\`, \`limit\`, \`cursor\`: as in *List vulnerabilities*.

**Response \`200\`**: \`{"items": [...], "next_cursor": …}\`. Each item has \`id\`, \`internal_id\` (\`OP-xxxx\`, null until sent), \`name\`, \`client_name\`, \`status\`, \`start_date\`, \`end_date\` (dates \`AAAA-MM-DD\`), \`sent_at\`, \`vulnerability_count\`, \`fixed_count\`, \`created_at\`, \`updated_at\`.

**Example**

\`\`\`
curl -sS "https://<portal>/api/v1/reports?status=sent&limit=1" -H "X-API-Key: $PORTAL_KEY"
\`\`\`

\`\`\`
{
  "items": [
    {
      "id": "056c3eee-6d69-47c2-876a-f099dcbc45f9",
      "internal_id": "OP-0001",
      "name": "Pentest Aplicação Web - Portal do Cliente",
      "client_name": "Banco Aurora S.A.",
      "status": "sent",
      "start_date": "2026-08-03",
      "end_date": "2026-08-21",
      "sent_at": "2026-10-08T12:59:35.258463",
      "vulnerability_count": 3,
      "fixed_count": 0,
      "created_at": "2026-10-08T12:59:35.029437",
      "updated_at": "2026-10-08T12:59:35.204803"
    }
  ],
  "next_cursor": "MjAyNi0xMC0wOFQxMjo1OTozNS4yMDQ4MDN8MDU2YzNlZWUt…"
}
\`\`\``,
      },
      {
        id: 'api-ep-report', title: 'Read a report',
        md: `**\`GET /api/v1/reports/{ref}\`** · scope \`reports:read\`

One complete report.

**Parameters**: \`ref\` (path): UUID or number (\`OP-0001\`).

**Response \`200\`**: the summary fields plus:

- \`test_type\`, \`test_model\`, \`environment\`, \`demand_origin\`, \`scope\`.
- \`executive_summary_md\`, \`introduction_md\`: Markdown.
- \`sections\`: Additional Sections in order, \`{position, title, content_markdown}\`.
- \`operators\`: usernames.
- \`vulnerabilities\`: summaries of the report's vulnerabilities.
- \`attachments\`: the report's evidence, as in *A vulnerability's evidence*.

Internal notes are not sent.

**Errors**: \`404\` \`{"detail": "Report not found"}\`.

**Example**

\`\`\`
curl -sS https://<portal>/api/v1/reports/OP-0001 -H "X-API-Key: $PORTAL_KEY"
\`\`\`

\`\`\`
{
  "id": "056c3eee-6d69-47c2-876a-f099dcbc45f9",
  "internal_id": "OP-0001",
  "name": "Pentest Aplicação Web - Portal do Cliente",
  "client_name": "Banco Aurora S.A.",
  "status": "sent",
  "start_date": "2026-08-03",
  "end_date": "2026-08-21",
  "sent_at": "2026-10-08T12:59:35.258463",
  "vulnerability_count": 3,
  "fixed_count": 0,
  "created_at": "2026-10-08T12:59:35.029437",
  "updated_at": "2026-10-08T12:59:35.204803",
  "test_type": "Pentest",
  "test_model": "Gray box",
  "environment": "Homologação",
  "demand_origin": "Contratação anual",
  "scope": "banco-aurora-s.a..example",
  "executive_summary_md": "Foram identificadas vulnerabilidades que exigem **atenção prioritária**…",
  "introduction_md": "Resultados do trabalho realizado para **Banco Aurora S.A.**.",
  "sections": [
    {
      "position": 1,
      "title": "Metodologia",
      "content_markdown": "Testes manuais e automatizados, seguindo OWASP e PTES."
    }
  ],
  "operators": [
    "jonathan"
  ],
  "vulnerabilities": [
    {
      "id": "e4a61965-ab90-41f6-b0d3-d05db0816f74",
      "internal_id": "VULN-0074",
      "status": "sent",
      "identifier": "Falta de rate limiting - intranet",
      "cwe": "CWE-770",
      "cvss_score": 8.1,
      "source": "manual",
      "rvs_id": null,
      "report": {
        "id": "056c3eee-6d69-47c2-876a-f099dcbc45f9",
        "internal_id": "OP-0001",
        "name": "Pentest Aplicação Web - Portal do Cliente",
        "status": "sent"
      },
      "created_at": "2026-10-08T12:59:35.119620",
      "updated_at": "2026-10-08T12:59:35.204803"
    }
  ],
  "attachments": []
}
\`\`\``,
      },
      {
        id: 'api-ep-report-export', title: 'Export a report',
        md: `**\`GET /api/v1/reports/{ref}/export\`** · scope \`exports\`

The same files as the *Export* button: the report as PDF or Word, or its vulnerabilities as an Excel sheet. Recorded in the audit log.

**Parameters**: \`ref\` (path); \`format\` (query): \`pdf\` (default), \`xlsx\` or \`docx\`.

**Response \`200\`**: the file, with \`Content-Disposition\` (e.g. \`OP-0001_20261025.pdf\`, \`OP-0001_vulnerabilidades_20261025.xlsx\`).

**Errors**: \`404\`; \`422\` for another format.

**Example**

\`\`\`
curl -sS -o OP-0001.xlsx "https://<portal>/api/v1/reports/OP-0001/export?format=xlsx" \\
  -H "X-API-Key: $PORTAL_KEY"
\`\`\``,
      },
      {
        id: 'api-ep-health', title: 'Health check',
        md: `**\`GET /api/health\`** · no key

Answers \`200\` while the portal is up. Useful for monitoring.

**Example**

\`\`\`
curl -sS https://<portal>/api/health
\`\`\`

\`\`\`
{
  "status": "ok",
  "environment": "production"
}
\`\`\``,
      },
      {
        id: 'api-erros', title: 'Errors',
        md: `The error body always has \`detail\`: a text or, for format errors, a list with the field and the reason.

- \`401\`: missing, invalid, revoked or expired key. \`{"detail": "Invalid or missing API key"}\`
- \`403\`: the key lacks the endpoint's scope. \`{"detail": "This API key lacks the scope 'rvs:write'"}\`
- \`404\`: the record doesn't exist (or was deleted).
- \`409\`: the action doesn't fit the current status, e.g. an RVS ID on a vulnerability not sent, or already set.
- \`413\`: body over 1 MB.
- \`422\`: invalid data or parameters (an invalid \`cursor\` included). Examples:

\`\`\`
{"detail": "Required for status 'ready': description, finding_detail, mitigation"}
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
        md: `Menu ➝ *Audit Logs*. Records sign-ins, creations, changes, status changes, sends, exports, attachment reads and reservation releases, with who did it (a user, or \`api:<prefix>\` for keys), when and from which IP. Filter by type of action.`,
      },
    ],
  },
]

export const DOCS = { 'pt-BR': pt, en }
