<!-- page: api -->
# A API de integração

O portal não vive isolado. Scanners encontram vulnerabilidades, sistemas de chamados acompanham correções, planilhas de semestres passados guardam histórico. A **API de integração** é a porta para esses sistemas. Por ela, um programa pode ler vulnerabilidades e relatórios, baixar evidências e documentos, registrar IDs de RVS, criar e editar vulnerabilidades, agrupá-las em lotes e importar vulnerabilidades antigas com o seu histórico.

A API fica em `/api/v1` e é separada da que o próprio portal usa. Um programa não entra com login e senha, mas com uma **chave de API**, criada por um administrador e limitada aos **escopos** de que aquele programa precisa. Uma chave só funciona em `/api/v1`; nenhuma outra parte do portal a aceita.

Este capítulo começa pelo que vale para a API toda (chaves, autenticação, formatos e paginação) e depois percorre os endpoints, agrupados pelo que fazem. Se você vai escrever uma integração, leia as duas primeiras seções antes; as outras servem de referência. Esta tabela resume todos os endpoints:

| Endpoint | Escopo | Seção |
|---|---|---|
| `GET /api/v1/vulnerabilities` | `vulns:read` | [Lendo vulnerabilidades](#api-ler) |
| `GET /api/v1/vulnerabilities/{ref}` | `vulns:read` | [Lendo vulnerabilidades](#api-ler) |
| `GET /api/v1/vulnerabilities/{ref}/attachments` | `vulns:read` | [Lendo vulnerabilidades](#api-ler) |
| `GET /api/v1/attachments/{id}/content` | `vulns:read` ou `reports:read` | [Lendo vulnerabilidades](#api-ler) |
| `GET /api/v1/vulnerabilities/{ref}/export` | `exports` | [Lendo vulnerabilidades](#api-ler) |
| `POST /api/v1/vulnerabilities` | `vulns:write` | [Criar e editar](#api-criar), [Importar](#api-importar) |
| `PATCH /api/v1/vulnerabilities/{ref}` | `vulns:write` | [Criar e editar](#api-criar) |
| `POST /api/v1/batches` | `vulns:write` | [Lotes](#api-lotes) |
| `GET /api/v1/rvs-queue` | `rvs:write` ou `vulns:read` | [A fila de RVS](#api-rvs) |
| `POST /api/v1/vulnerabilities/{ref}/rvs` | `rvs:write` | [A fila de RVS](#api-rvs) |
| `GET /api/v1/reports` | `reports:read` | [Lendo relatórios](#api-relatorios) |
| `GET /api/v1/reports/{ref}` | `reports:read` | [Lendo relatórios](#api-relatorios) |
| `GET /api/v1/reports/{ref}/export` | `exports` | [Lendo relatórios](#api-relatorios) |
| `GET /api/health` | nenhum | [Erros e monitoração](#api-erros) |

<!-- page: api-chaves -->
# Chaves, escopos e autenticação

Toda chamada à API leva uma chave, e é a chave que decide o que a chamada pode fazer. Só um administrador cria chaves, na página **Chaves de API**: ele dá um nome à chave, escolhe os escopos e, se quiser, uma data de expiração. A chave completa aparece uma única vez, logo depois de criada. O portal guarda apenas um hash dela e os oito primeiros caracteres, o prefixo, que identificam a chave nas listas e nos logs.

## Escopos

Um escopo é uma permissão. Cada endpoint exige um, e uma chave só faz o que os seus escopos permitem.

| Escopo | Permite |
|---|---|
| `vulns:read` | Ler vulnerabilidades e as suas evidências |
| `vulns:write` | Criar e editar vulnerabilidades e criar lotes |
| `vulns:import` | Junto com `vulns:write`, importar vulnerabilidades antigas com status, datas, número e RVS |
| `rvs:write` | Ver a fila de RVS e registrar IDs de RVS |
| `reports:read` | Ler relatórios e as suas evidências |
| `exports` | Baixar documentos em PDF, Word e Excel |

A regra é dar a cada sistema só o que ele usa. Um sistema de chamados que apenas registra RVS precisa só de `rvs:write`; um scanner que cria achados precisa só de `vulns:write`. O escopo `vulns:import` pede um cuidado a mais, porque permite criar vulnerabilidades com datas e números do passado: dê-o apenas à chave do script de importação, e revogue essa chave quando a importação terminar.

Uma chave lê todos os registros que o seu escopo permite. As restrições por pessoa, dos papéis Editor e Leitor restritos, valem para pessoas e não para sistemas.

## Autenticação

A chave vai no cabeçalho `X-API-Key` de cada requisição. Quando há corpo, ele é JSON:

```
X-API-Key: <sua chave>
Content-Type: application/json
```

Uma chave ausente, desconhecida, revogada ou expirada recebe sempre a mesma resposta, `401`, para que ninguém descubra por tentativa quais chaves existem. Uma chave válida, mas sem o escopo do endpoint, recebe `403`, com o nome do escopo que faltou. Fora de `/api/v1`, nenhuma chave funciona, qualquer que seja o escopo.

## O que fica registrado

As ações de uma chave ficam nos logs de auditoria como as de uma pessoa, com o autor `api:<prefixo>`: criações, edições, registros de RVS, exportações e downloads de evidência. As vulnerabilidades criadas pela API pertencem ao administrador que emitiu a chave.

<!-- page: api-convencoes -->
# Formatos, paginação e sincronização

Algumas regras valem para todos os endpoints, e conhecê-las de antemão poupa surpresas.

Onde um caminho tem `{ref}`, você pode usar o UUID do registro ou o seu ID interno, como `VULN-0012` ou `OP-0003`, sem diferenciar maiúsculas. Corpos e respostas são JSON em UTF-8. As datas e horas das respostas estão sempre em UTC; nos parâmetros, você pode enviá-las com `Z` ou com fuso, e o portal converte.

As respostas da API têm um formato próprio, separado do que a interface do portal usa, para que uma integração não quebre quando a interface muda. Elas nunca trazem as notas internas nem a lista *Compartilhado com*, assim como as exportações.

## Paginação

As listas, `/vulnerabilities` e `/reports`, vêm em ordem de última alteração e em páginas:

```
{"items": [ ... ], "next_cursor": "MjAyNi0xMC0wOF..."}
```

O parâmetro `limit` diz quantos itens vêm por página, de 1 a 200 (o padrão é 50). Para a página seguinte, passe o `next_cursor` recebido no parâmetro `cursor`. Quando `next_cursor` vem `null`, a lista acabou. As listas trazem um resumo de cada registro; para o conteúdo completo, leia o registro pelo seu `{ref}`.

## Sincronização

A ordem por última alteração torna simples manter outro sistema em dia. O parâmetro `updated_since` restringe a lista ao que foi criado ou alterado a partir de um momento, em ISO 8601, como `2026-10-25T14:00:00Z`. Guarde o `updated_at` do último item que você processou e, na execução seguinte, peça `updated_since` com esse valor, seguindo `next_cursor` até o fim. Um registro alterado de novo volta a aparecer, então o seu sistema sempre recebe a versão mais recente.

Em Python, a leitura de tudo o que mudou desde um momento fica assim:

```
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
```

<!-- page: api-ler -->
# Lendo vulnerabilidades

Quatro endpoints, todos com o escopo `vulns:read`, leem vulnerabilidades e as suas evidências; um quinto, com o escopo `exports`, baixa o documento de uma vulnerabilidade.

## Listar vulnerabilidades

`GET /api/v1/vulnerabilities` lista as vulnerabilidades que não foram excluídas, em páginas e em ordem de última alteração. Os parâmetros, todos opcionais, filtram a lista:

| Parâmetro | Filtra por |
|---|---|
| `status` | Um ou mais status; repita o parâmetro para vários, como em `status=sent&status=fixing` |
| `source` | Fonte que contém o texto, sem diferenciar maiúsculas |
| `report` | UUID ou número de um relatório; `none` para as que não estão em relatório |
| `batch` | Um lote, como `BATCH-0001`, sem diferenciar maiúsculas; `none` para as que não vieram em lote |
| `cvss_min` | CVSS maior ou igual, de 0 a 10 |
| `updated_since` | Criadas ou alteradas a partir desse momento |
| `limit`, `cursor` | A paginação, como em [Formatos, paginação e sincronização](#api-convencoes) |

Cada item da resposta é um resumo da vulnerabilidade. Os status possíveis são `draft`, `ready`, `sent`, `fixing`, `retesting`, `fixed` e `risk_accepted`. O `internal_id` é nulo enquanto a vulnerabilidade é um rascunho, e o `rvs_id`, até o registro do RVS. O campo `report` traz o relatório a que ela pertence, ou nulo; `batch_id`, o lote em que ela veio; e `imported_at`, quando ela foi importada com o seu histórico.

```
curl -sS "https://<portal>/api/v1/vulnerabilities?status=fixing&limit=1" \
  -H "X-API-Key: $PORTAL_KEY"
```

```
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
      "batch_id": null,
      "imported_at": null,
      "created_at": "2026-10-08T12:59:30.258918",
      "updated_at": "2026-10-08T12:59:30.315866"
    }
  ],
  "next_cursor": "MjAyNi0xMC0wOFQxMjo1OTozMC4zMTU4NjZ8OTIxNTc0Mjgt…"
}
```

Um status, uma data ou um cursor inválido recebe `422`, e um relatório inexistente em `report`, `404`.

## Ler uma vulnerabilidade

`GET /api/v1/vulnerabilities/{ref}` devolve a vulnerabilidade completa. Além dos campos do resumo, ela traz os textos em Markdown (`description`, `finding_detail` e `mitigation`), as `references`, o `cvss_vector`, os `operators` pelos seus logins, os `metadata` enviados pela ferramenta que a criou e a data em que ela entrou em cada status: `ready_at`, `sent_at`, `accepted_at`, `fixing_at`, `retesting_at`, `fixed_at` e `risk_accepted_at`. Se a defesa assumiu o risco, a justificativa vem em `risk_reason`. Uma vulnerabilidade inexistente recebe `404`.

```
curl -sS https://<portal>/api/v1/vulnerabilities/VULN-0003 -H "X-API-Key: $PORTAL_KEY"
```

```
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
  "batch_id": null,
  "imported_at": null,
  "created_at": "2026-10-08T12:59:30.258918",
  "updated_at": "2026-10-08T12:59:30.315866",
  "description": "Conteúdo persistido e renderizado sem escape.",
  "finding_detail": "Identificado em bi. Reprodução: requisição ao endpoint /bi/v2/recurso/…",
  "mitigation": "Sanitizar na entrada e escapar na saída.",
  "references": [],
  "cvss_vector": "AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:N",
  "operators": ["benjamin", "michelle"],
  "metadata": {},
  "ready_at": "2026-10-08T12:59:30.282810",
  "sent_at": "2026-10-08T12:59:30.301332",
  "accepted_at": "2026-10-08T12:59:30.319272",
  "fixing_at": "2026-10-08T12:59:30.319272",
  "retesting_at": null,
  "fixed_at": null,
  "risk_accepted_at": null,
  "risk_reason": null
}
```

## Evidências

`GET /api/v1/vulnerabilities/{ref}/attachments` lista os arquivos anexados à vulnerabilidade, do mais antigo ao mais novo, cada um com `id`, `filename`, `display_name`, `mime_type`, `size_bytes` e `created_at`:

```
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
```

Para baixar um arquivo, use o seu `id` em `GET /api/v1/attachments/{id}/content`. A resposta é o próprio arquivo, com o seu `Content-Type` e `Content-Disposition: attachment`. A evidência de uma vulnerabilidade exige `vulns:read`, e a de um relatório, `reports:read`; sem o escopo do dono do arquivo, a resposta é `404`, como se ele não existisse. Cada download fica nos logs de auditoria.

```
curl -sS -o login-burp.png \
  https://<portal>/api/v1/attachments/3f1c2a9e-5b7d-4e61-9a0c-2d8e4b6f1a73/content \
  -H "X-API-Key: $PORTAL_KEY"
```

## Exportar

`GET /api/v1/vulnerabilities/{ref}/export`, com o escopo `exports`, devolve o mesmo arquivo do botão *Exportar*, com as imagens de evidência. O parâmetro `format` escolhe entre `pdf`, o padrão, e `docx`; outro formato recebe `422`. O nome do arquivo vem no `Content-Disposition`, como `VULN-0002.docx`, e a exportação fica nos logs de auditoria.

```
curl -sS -o VULN-0002.pdf "https://<portal>/api/v1/vulnerabilities/VULN-0002/export?format=pdf" \
  -H "X-API-Key: $PORTAL_KEY"
```

<!-- page: api-criar -->
# Criar e editar vulnerabilidades

Um scanner ou outra ferramenta pode registrar os seus achados diretamente no portal, sem que alguém precise copiá-los à mão. Com o escopo `vulns:write`, `POST /api/v1/vulnerabilities` cria uma vulnerabilidade, e `PATCH /api/v1/vulnerabilities/{ref}` edita uma que ainda não foi enviada.

## Criar

O corpo é um objeto JSON de até 1 MB, com os mesmos campos do formulário do portal. Todos são opcionais, mas pelo menos um entre `identifier`, `description` e `finding_detail` precisa vir preenchido: uma vulnerabilidade sem nenhum deles não diria nada.

| Campo | Conteúdo |
|---|---|
| `identifier` | O nome do achado ou um CVE, até 500 caracteres |
| `description` | A Descrição, em Markdown, até 100.000 caracteres; o mesmo vale para os dois seguintes |
| `finding_detail` | Os Detalhes do Achado |
| `mitigation` | A Mitigação / Solução |
| `cwe` | `CWE-79` ou só `79`; o portal guarda como `CWE-79` |
| `cvss_score` | A nota, de 0 a 10 |
| `cvss_vector` | O vetor, até 200 caracteres |
| `references` | Até 50 URLs, cada uma começando com `http://` ou `https://` |
| `source` | A ferramenta de origem, como `nuclei` ou `burp`; é o que o filtro `source:` procura |
| `internal_notes` | As notas internas, em Markdown |
| `operators` | Até 20 logins de usuários ativos com papel Administrador, Editor (todos) ou Editor restrito |
| `status` | `draft`, o padrão, ou `ready` |
| `batch_id` | O lote desta execução (veja [Lotes](#api-lotes)) |
| `metadata` | Um objeto livre, guardado como veio, até 64 KB |

O `status` merece atenção. Uma vulnerabilidade criada como `draft` espera que um analista a revise no portal, e é o mais indicado quando o achado veio de uma ferramenta automática. Criada como `ready`, ela já precisa de `identifier`, `description` e `finding_detail`, os mesmos campos que o botão *Concluir* exige, e recebe o seu ID interno na hora. Uma criação comum nunca gera uma vulnerabilidade já enviada; para trazer uma antiga com o seu histórico, use a [importação](#api-importar).

Campos que o portal não conhece não são recusados: eles vão para os metadados, junto com o objeto `metadata`. Assim, uma ferramenta pode enviar os seus próprios dados, como o host ou o template que gerou o achado, sem que o portal precise conhecê-los.

```
curl -sS -X POST https://<portal>/api/v1/vulnerabilities \
  -H "X-API-Key: $PORTAL_KEY" -H "Content-Type: application/json" \
  -d '{"identifier": "Exposed .git directory", "source": "nuclei", "cwe": "527",
       "cvss_score": 5.3, "operators": ["jonathan"], "host": "app.example.com"}'
```

A resposta, com o status `201`, traz o `id` da vulnerabilidade, que também é o seu endereço no portal (`/vulnerabilities/<id>`), e o `internal_id`, presente só quando ela foi criada como `ready`:

```
{"id": "72643b23-af52-42d9-a139-c1aea6f70a15", "internal_id": null, "status": "draft", "batch_id": null, "imported": false}
```

Não há deduplicação: repetir a mesma requisição cria outra vulnerabilidade. Se uma criação falhou por um erro de rede, confira se ela chegou, com o filtro `source`, antes de reenviar.

## Editar

`PATCH /api/v1/vulnerabilities/{ref}` muda só os campos enviados, com os mesmos nomes e regras da criação; o que não vem no corpo fica como está. É assim que uma ferramenta corrige um achado que registrou, completa um campo ou move uma vulnerabilidade de lote: `"batch_id": "BATCH-0004"` a coloca num lote existente, e `"batch_id": null` a tira do lote. A lista de `operators`, quando enviada, substitui a anterior. A resposta é a vulnerabilidade completa, como na leitura.

```
curl -sS -X PATCH https://<portal>/api/v1/vulnerabilities/VULN-0042 \
  -H "X-API-Key: $PORTAL_KEY" -H "Content-Type: application/json" \
  -d '{"cvss_score": 7.5, "mitigation": "Atualizar a biblioteca para a versão 2.4."}'
```

A edição tem limites, que protegem o que já foi entregue e o trabalho de quem está no portal. Só vulnerabilidades em rascunho ou prontas, fora de relatório, podem ser editadas. Uma já enviada recebe `409`, e uma dentro de um relatório em rascunho também; esta se edita no portal, com a reserva do relatório. Uma vulnerabilidade pronta precisa continuar com `identifier`, `description` e `finding_detail`, e um rascunho, com pelo menos um deles. O ciclo de vida continua no portal, então `status`, os campos de importação e campos desconhecidos recebem `422`.

Se outra pessoa pode estar mexendo na mesma vulnerabilidade, envie `if_updated_at` com o `updated_at` que você leu por último. Se o registro mudou desde então, nada é gravado e a resposta é `409`: leia de novo e decida. Do outro lado, quem estiver editando a vulnerabilidade no portal recebe o aviso de conflito ao salvar.

Um pedido que não muda nada não cria versão nem entrada de auditoria. Cada mudança real fica nos logs, com a chave como autora, e uma troca de lote aparece como `{"from", "to"}`.

<!-- page: api-lotes -->
# Lotes

Uma ferramenta costuma registrar muitos achados numa mesma execução, como um scan de rede ou uma varredura de um domínio. Um **lote** agrupa as vulnerabilidades de uma execução, para que depois seja fácil encontrar, revisar e acompanhar tudo o que veio junto.

O lote é criado antes das vulnerabilidades. `POST /api/v1/batches`, com o escopo `vulns:write` e sem corpo, cria um lote novo e devolve o número que o portal deu a ele:

```
{"batch_id": "BATCH-0001", "created_at": "2026-11-24T19:30:04.949885"}
```

Em seguida, a ferramenta envia esse `batch_id` em cada `POST /api/v1/vulnerabilities` da execução. O número aceita maiúsculas ou minúsculas, e um lote que não existe recebe `422`. Este script cria um lote e registra nele um achado para cada arquivo JSON da pasta:

```
BATCH=$(curl -sS -X POST https://<portal>/api/v1/batches -H "X-API-Key: $PORTAL_KEY" | jq -r .batch_id)
for f in achados/*.json; do
  jq --arg b "$BATCH" '. + {batch_id: $b}' "$f" |
    curl -sS -X POST https://<portal>/api/v1/vulnerabilities \
      -H "X-API-Key: $PORTAL_KEY" -H "Content-Type: application/json" -d @-
done
```

Para ler um lote, filtre a lista: `GET /api/v1/vulnerabilities?batch=BATCH-0001`. No portal, o mesmo filtro é `batch:BATCH-0001`, nas Operações, e cada vulnerabilidade mostra o seu lote no topo da página.

## Mudando o lote depois

O lote de uma vulnerabilidade é assunto da integração, e por isso só muda pela API, nunca pelo formulário do portal. Enquanto a vulnerabilidade está em rascunho ou pronta, um [PATCH](#api-criar) com `batch_id` a move para outro lote, e `null` a tira do lote. Este script passa o lote `BATCH-0003` inteiro para o `BATCH-0004`:

```
curl -sS "https://<portal>/api/v1/vulnerabilities?batch=BATCH-0003&limit=200" -H "X-API-Key: $PORTAL_KEY" |
  jq -r '.items[].id' | while read id; do
    curl -sS -X PATCH "https://<portal>/api/v1/vulnerabilities/$id" \
      -H "X-API-Key: $PORTAL_KEY" -H "Content-Type: application/json" -d '{"batch_id": "BATCH-0004"}'
  done
```

<!-- page: api-importar -->
# Importar vulnerabilidades antigas

Quando o portal chega, o trabalho de semestres anteriores já existe em outro lugar, numa planilha ou num sistema antigo. Para que os dashboards e as linhas do tempo contem a história completa, essas vulnerabilidades podem ser **importadas** como terminaram: com o status final, a data de cada etapa, o número original e o RVS.

A importação usa o mesmo endpoint e o mesmo corpo da [criação](#api-criar), `POST /api/v1/vulnerabilities`, com alguns campos a mais. Esses campos exigem que a chave tenha, além de `vulns:write`, o escopo `vulns:import`; sem ele, qualquer um deles recebe `403`.

| Campo | Conteúdo |
|---|---|
| `status` | Qualquer status: `draft`, `ready`, `sent`, `fixing`, `retesting`, `fixed` ou `risk_accepted` |
| `internal_id` | O número original, como `VULN-0042`; sem ele, a vulnerabilidade recebe o próximo número, e um rascunho não tem número |
| `created_at`, `ready_at`, `sent_at` | As datas de criação, de conclusão e de envio |
| `accepted_at`, `fixing_at` | A aceitação pela defesa e o início da correção |
| `retesting_at`, `fixed_at` | O pedido de reteste e a correção |
| `risk_accepted_at` | Quando a defesa assumiu o risco |
| `updated_at` | A última alteração; por padrão, a última das datas |
| `rvs_id` | O RVS, obrigatório em `fixing`, `retesting` e `fixed` |
| `accepted_by`, `risk_accepted_by` | Os logins de quem aceitou ou assumiu o risco, se forem usuários do portal |
| `risk_reason` | A justificativa, obrigatória em `risk_accepted` |

As datas usam ISO 8601, com `Z` ou com fuso, e são convertidas para UTC. Nenhuma pode estar no futuro.

## As datas precisam contar uma história coerente

O portal confere se as datas fazem sentido para o status. Cada status exige as datas das etapas que levam até ele, e nenhuma das etapas que viriam depois. Uma vulnerabilidade `sent` precisa de `created_at`, `ready_at` e `sent_at`, e pode ter `accepted_at`. Uma em `fixing` precisa também de `fixing_at` e do `rvs_id`; o `accepted_at`, se não vier, fica igual ao `fixing_at`. Em `retesting`, ela precisa também de `retesting_at`. Uma `fixed` precisa de `created_at`, `ready_at`, `sent_at`, `fixing_at`, `fixed_at` e `rvs_id`, e o reteste é opcional. Uma `risk_accepted` precisa de `created_at`, `ready_at`, `sent_at`, `risk_accepted_at` e da `risk_reason`.

As datas também precisam seguir a ordem do ciclo: criada, pronta, enviada, aceita, em correção, em reteste, corrigida, com o risco assumido depois do envio. Quando algo não bate, a resposta `422` lista todos os problemas de uma vez, para que você corrija a planilha numa passada só. Fora do rascunho, valem também os campos obrigatórios de sempre: `identifier`, `description` e `finding_detail`.

## O número original

Com `internal_id`, a vulnerabilidade mantém o número que tinha, e os números seguintes do portal passam a vir depois do maior número importado, para que nunca haja dois iguais. Um número que já existe recebe `409`, e o mesmo acontece com um RVS que já pertence a outra vulnerabilidade.

## O que a importação não faz

A importação não entrega nada a ninguém: nenhum e-mail é enviado. Ela também não inventa histórico. Os logs de auditoria têm uma única entrada de criação, marcada com `"import": true`, e não uma por etapa. A vulnerabilidade guarda a data da importação em `imported_at`, que aparece nas leituras da API e como *Importada em …* na página dela, e a resposta traz `"imported": true`. Vulnerabilidades importadas são avulsas, sem relatório. Se uma vulnerabilidade passou por correções que falharam no passado, elas não viram eventos; anote-as em `internal_notes` ou nos `metadata`.

```
curl -sS -X POST https://<portal>/api/v1/vulnerabilities \
  -H "X-API-Key: $IMPORT_KEY" -H "Content-Type: application/json" \
  -d '{"identifier": "SQL injection em Portal do Cliente", "description": "…", "finding_detail": "…",
       "status": "fixed", "internal_id": "VULN-0042", "rvs_id": "RVS-2025-00017",
       "created_at": "2025-03-03T14:00:00-03:00", "ready_at": "2025-03-04T10:00:00-03:00",
       "sent_at": "2025-03-05T09:00:00-03:00", "fixing_at": "2025-03-12T16:00:00-03:00",
       "retesting_at": "2025-04-01T10:00:00-03:00", "fixed_at": "2025-04-02T11:00:00-03:00",
       "internal_notes": "Importada da planilha de 2025S1"}'
```

```
{"id": "…", "internal_id": "VULN-0042", "status": "fixed", "batch_id": null, "imported": true}
```

Antes de importar um semestre inteiro, teste com poucas vulnerabilidades. Use uma chave só para a importação, com data de expiração, e revogue-a quando terminar.

<!-- page: api-rvs -->
# A fila de RVS

Quando a organização acompanha as correções num sistema de chamados, é esse sistema que sabe o número do RVS aberto para cada vulnerabilidade. Dois endpoints permitem que ele registre o RVS diretamente no portal, sem que alguém do time de defesa precise digitá-lo.

`GET /api/v1/rvs-queue`, com o escopo `rvs:write` ou `vulns:read`, lista as vulnerabilidades enviadas que ainda não têm RVS, da enviada há mais tempo para a mais recente. A lista não é paginada, e cada item tem os campos do resumo de [Lendo vulnerabilidades](#api-ler).

```
curl -sS https://<portal>/api/v1/rvs-queue -H "X-API-Key: $PORTAL_KEY"
```

```
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
    "batch_id": null,
    "imported_at": null,
    "created_at": "2026-10-08T12:59:30.068791",
    "updated_at": "2026-10-08T12:59:30.108013"
  }
]
```

Com o RVS aberto, `POST /api/v1/vulnerabilities/{ref}/rvs`, com o escopo `rvs:write`, o registra. O corpo traz o ID, com 1 a 200 caracteres:

```
curl -sS -X POST https://<portal>/api/v1/vulnerabilities/VULN-0001/rvs \
  -H "X-API-Key: $PORTAL_KEY" -H "Content-Type: application/json" \
  -d '{"rvs_id": "RVS-2026-001"}'
```

A vulnerabilidade passa para *Em correção*, e a resposta é a vulnerabilidade completa, com `"status": "fixing"` e o `rvs_id`. Registrar o RVS também conta como aceitar a vulnerabilidade, assim como quando o time de defesa o faz pelo portal. O registro fica nos logs de auditoria, e o ID não pode ser alterado depois.

Como o RVS só pode ser registrado uma vez, e só numa vulnerabilidade enviada, as tentativas fora dessas condições recebem `409`: numa vulnerabilidade que não está enviada, numa que já tem RVS, ou com um ID que já pertence a outra vulnerabilidade. Um `rvs_id` vazio recebe `422`.

<!-- page: api-relatorios -->
# Lendo relatórios

Pela API, os relatórios são apenas lidos: criá-los, editá-los e enviá-los continua sendo trabalho do Red Team no portal. Com o escopo `reports:read`, uma integração pode listá-los e lê-los, e com `exports`, baixar os seus documentos.

## Listar relatórios

`GET /api/v1/reports` lista os relatórios que não foram excluídos, em páginas e em ordem de última alteração. O parâmetro `status` filtra por `draft` ou `sent` (repita-o para os dois), e `client` procura no nome do cliente. A paginação e o `updated_since` funcionam como em [Formatos, paginação e sincronização](#api-convencoes).

Cada item traz o `internal_id` (`OP-xxxx`, nulo até o envio), o nome, o cliente, o status, as datas da operação no formato `AAAA-MM-DD`, a data de envio e três contagens: `vulnerability_count`, quantas vulnerabilidades o relatório tem, `fixed_count`, quantas já foram corrigidas, e `closed_count`, quantas estão corrigidas ou com o risco assumido.

```
curl -sS "https://<portal>/api/v1/reports?status=sent&limit=1" -H "X-API-Key: $PORTAL_KEY"
```

```
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
      "closed_count": 0,
      "created_at": "2026-10-08T12:59:35.029437",
      "updated_at": "2026-10-08T12:59:35.204803"
    }
  ],
  "next_cursor": "MjAyNi0xMC0wOFQxMjo1OTozNS4yMDQ4MDN8MDU2YzNlZWUt…"
}
```

## Ler um relatório

`GET /api/v1/reports/{ref}` devolve o relatório completo. Além dos campos do resumo, ele traz os dados da operação (`test_type`, `test_model`, `environment`, `demand_origin` e `scope`), o sumário executivo e a introdução em Markdown (`executive_summary_md` e `introduction_md`), as seções adicionais em ordem, os operadores, o resumo de cada vulnerabilidade do relatório e a lista das suas evidências. Como em toda a API, as notas internas não vêm. Um relatório inexistente recebe `404`.

```
curl -sS https://<portal>/api/v1/reports/OP-0001 -H "X-API-Key: $PORTAL_KEY"
```

```
{
  "id": "056c3eee-6d69-47c2-876a-f099dcbc45f9",
  "internal_id": "OP-0001",
  "name": "Pentest Aplicação Web - Portal do Cliente",
  "client_name": "Banco Aurora S.A.",
  "status": "sent",
  "…": "os demais campos do resumo",
  "test_type": "Pentest",
  "test_model": "Gray box",
  "environment": "Homologação",
  "demand_origin": "Contratação anual",
  "scope": "banco-aurora-s.a..example",
  "executive_summary_md": "Foram identificadas vulnerabilidades que exigem **atenção prioritária**…",
  "introduction_md": "Resultados do trabalho realizado para **Banco Aurora S.A.**.",
  "sections": [
    {"position": 1, "title": "Metodologia", "content_markdown": "Testes manuais e automatizados, seguindo OWASP e PTES."}
  ],
  "operators": ["jonathan"],
  "vulnerabilities": [
    {"id": "e4a61965-ab90-41f6-b0d3-d05db0816f74", "internal_id": "VULN-0074", "status": "sent", "…": "o resumo de cada uma"}
  ],
  "attachments": []
}
```

## Exportar

`GET /api/v1/reports/{ref}/export`, com o escopo `exports`, devolve os mesmos arquivos do botão *Exportar*. O parâmetro `format` escolhe o relatório em `pdf`, o padrão, ou em `docx`, ou a planilha das vulnerabilidades em `xlsx`. O nome do arquivo vem no `Content-Disposition`, como `OP-0001_20261025.pdf` ou `OP-0001_vulnerabilidades_20261025.xlsx`.

```
curl -sS -o OP-0001.xlsx "https://<portal>/api/v1/reports/OP-0001/export?format=xlsx" \
  -H "X-API-Key: $PORTAL_KEY"
```

<!-- page: api-erros -->
# Erros, monitoração e boas práticas

Quando algo dá errado, a resposta tem um código HTTP, que diz o tipo do problema, e um corpo com o campo `detail`, que diz o problema em si. Na maioria das vezes, `detail` é um texto; nos erros de formato, como um número fora do limite, é uma lista com o campo e o motivo.

| Código | Significa |
|---|---|
| `401` | A chave está ausente, é inválida, foi revogada ou expirou |
| `403` | A chave não tem o escopo do endpoint, ou o de importação para os campos enviados |
| `404` | O registro não existe ou foi excluído |
| `409` | A ação não cabe no estado atual do registro |
| `413` | O corpo passa de 1 MB |
| `422` | Dados ou parâmetros inválidos, inclusive um `cursor` inválido |

O `409` aparece em situações como registrar o RVS de uma vulnerabilidade que não está enviada, editar uma que já foi enviada, enviar um `if_updated_at` desatualizado ou importar um número ou um RVS que já existe. Estes são alguns exemplos de `detail` num `422`:

```
{"detail": "Required for status 'ready': description, finding_detail"}
{"detail": "unknown operator(s): nobody; operator(s) not active writers: isabella"}
{"detail": "status 'fixed' needs: fixing_at; sent_at is after fixing_at"}
{"detail": [{"loc": ["body", "cvss_score"], "msg": "Input should be less than or equal to 10", ...}]}
```

## Verificar o portal

`GET /api/health` não precisa de chave e responde `200` enquanto o portal está no ar, o que serve para monitoração:

```
curl -sS https://<portal>/api/health
```

```
{"status": "ok", "environment": "production"}
```

## Boas práticas

Use uma chave por sistema, só com os escopos que ele usa e com data de expiração, e revogue as que deixarem de ser usadas. Nunca coloque a chave no código ou num repositório: leia-a de uma variável de ambiente ou de um cofre de segredos.

Para manter outro sistema em dia, use `updated_since` e `next_cursor` em vez de baixar tudo a cada execução. Quando um achado ainda precisa da revisão de um analista, crie-o como `draft`, e numa execução com vários achados, crie um lote e envie o seu `batch_id` em cada um.

Lembre-se de que não há deduplicação: depois de um erro de rede, confira se a vulnerabilidade chegou antes de reenviá-la. E, para importar, use uma chave dedicada, teste com poucas vulnerabilidades e revogue a chave no fim.
