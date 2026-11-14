"""Sample text for the development data set (fictional clients and systems).

The text is about risk, ownership and remediation only: it fills the screens and exports with
realistic volume and deliberately holds no exploitation steps.
"""

# (control area, CWE)
TOPICS = [
    ("Controle de acesso insuficiente", "CWE-284"),
    ("Validação de entrada incompleta", "CWE-20"),
    ("Gestão de sessão inadequada", "CWE-613"),
    ("Autenticação fraca", "CWE-287"),
    ("Exposição de informações técnicas", "CWE-200"),
    ("Armazenamento inseguro de dados sensíveis", "CWE-312"),
    ("Segredos sem rotação", "CWE-798"),
    ("Criptografia desatualizada", "CWE-327"),
    ("Configuração padrão mantida", "CWE-1188"),
    ("Componente sem atualização de segurança", "CWE-1104"),
    ("Privilégios excessivos", "CWE-250"),
    ("Registro de eventos insuficiente", "CWE-778"),
    ("Segmentação de rede insuficiente", "CWE-923"),
    ("Monitoramento sem cobertura", "CWE-223"),
]

# (CVSS 3.1 vector, score)
SEVERITIES = [
    ("CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:C/C:H/I:H/A:H", 9.9),
    ("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H", 9.8),
    ("CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:N", 8.1),
    ("CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:L/A:N", 7.1),
    ("CVSS:3.1/AV:L/AC:L/PR:L/UI:N/S:U/C:H/I:N/A:N", 5.5),
    ("CVSS:3.1/AV:N/AC:L/PR:L/UI:R/S:C/C:L/I:L/A:N", 5.4),
    ("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N", 5.3),
    ("CVSS:3.1/AV:N/AC:H/PR:N/UI:R/S:U/C:L/I:N/A:N", 3.1),
]

DESCRIPTION = [
    "A avaliação de **$app** identificou uma deficiência em **$topic**. O controle existe, mas não é aplicado de forma uniforme em todas as funções do sistema, o que deixa parte do fluxo de negócio fora da proteção esperada pela política interna de segurança.",
    "A causa mais provável é histórica: a solução cresceu por entregas sucessivas, conduzidas por equipes diferentes, sem um componente central responsável por esse controle. Cada módulo acabou adotando a própria implementação.",
    "O ponto foi discutido com a equipe responsável durante o teste, que confirmou que o comportamento não é intencional e que não há controle compensatório formalmente documentado.",
    "O risco é agravado pela criticidade dos dados tratados, que incluem informações cadastrais e financeiras sujeitas à LGPD e às normas internas de classificação da informação.",
]

DETAIL = [
    "## Contexto\n\nA análise cobriu **$app** no ambiente acordado, com as credenciais de teste fornecidas para o projeto. A verificação foi feita em janela combinada, sem indisponibilidade e sem alteração de dados de clientes.",
    "## Ambiente afetado\n\n- Sistema: $app\n- Área responsável: $client\n- Ambiente: $environment\n- Janela de verificação: acordada com a equipe responsável",
    "## Observações\n\nA condição foi observada em mais de um módulo, com o mesmo comportamento. Os detalhes técnicos da reprodução ficam com a equipe do Red Team e são compartilhados com os responsáveis pela correção por canal seguro.\n\n> Nenhum dado de cliente foi retido ao final da verificação.",
    "## Impacto para o negócio\n\nCaso a condição seja explorada, os efeitos esperados são exposição de dados, descumprimento de requisitos regulatórios e perda de confiança dos clientes. A área de negócio classificou o processo afetado como **relevante**, e sua interrupção teria efeito direto no atendimento.",
    "## Fatores que reduzem o risco\n\n- O acesso ao sistema é restrito a usuários cadastrados.\n- Há trilha de auditoria para as principais operações.\n- A equipe de monitoramento recebe parte dos eventos gerados pela aplicação.",
]

MITIGATION = [
    "A correção deve tratar a causa e não apenas o ponto observado:\n\n1. Centralizar **$topic** em um componente único, reutilizado por todos os módulos.\n2. Revisar as funções existentes e registrar as exceções aprovadas.\n3. Incluir o controle nos critérios de aceite de novas entregas.\n4. Adicionar testes automatizados ao pipeline, para impedir regressões.",
    "## Prazo sugerido\n\nDe acordo com a política de gestão de vulnerabilidades, o prazo de correção depende da severidade. A equipe responsável deve registrar um plano de ação e informar o Blue Team sobre qualquer necessidade de exceção.",
    "## Validação\n\nConcluída a correção, solicite o reteste pelo portal. O Red Team repetirá a verificação no mesmo ambiente e registrará o resultado neste item.",
]

NOTES = [
    "Responsável técnico confirmou o recebimento na reunião de encerramento.",
    "Aguardando a definição de prioridade pela área de negócio.",
    "Item relacionado a uma entrega prevista para o próximo trimestre.",
]

REFERENCES = [
    "https://owasp.org/www-project-top-ten/",
    "https://cheatsheetseries.owasp.org/",
    "https://csrc.nist.gov/projects/cybersecurity-framework",
]

# name, client, app, type, model, environment, origin, sent days ago (None = draft),
# period length, vulnerability statuses
REPORTS = [
    dict(name="Avaliação do Portal do Cliente 2026", client="Diretoria de Canais Digitais", app="Portal do Cliente",
         test_type="web", test_model="graybox", environment="production", origin="Calendário anual", sent=120, days=20,
         statuses=["fixed"] * 7 + ["risk_accepted"]),
    dict(name="Avaliação das APIs de Parceiros", client="Diretoria de Plataformas Digitais", app="API de Parceiros",
         test_type="API", test_model="graybox", environment="staging", origin="Exigência regulatória", sent=75, days=15,
         statuses=["fixed"] * 3 + ["retesting"] * 3 + ["fixing"] * 2 + ["risk_accepted"]),
    dict(name="Avaliação do Aplicativo Conta Digital", client="Diretoria de Canais Digitais", app="Aplicativo Conta Digital",
         test_type="mobile", test_model="whitebox", environment="staging", origin="Novo lançamento", sent=42, days=12,
         statuses=["fixing"] * 4 + ["sent"] * 3),
    dict(name="Avaliação da Infraestrutura Corporativa", client="Diretoria de Infraestrutura", app="Infraestrutura Corporativa",
         test_type="infra", test_model="graybox", environment="production", origin="Calendário anual", sent=21, days=25,
         statuses=["fixing"] * 3 + ["retesting"] + ["sent"] * 5),
    dict(name="Avaliação da Rede do Data Center", client="Diretoria de Infraestrutura", app="Rede do Data Center",
         test_type="infra", test_model="blackbox", environment="production", origin="Pedido da área", sent=10, days=10,
         statuses=["sent"] * 6),
    dict(name="Avaliação da Landing Zone em Nuvem", client="Diretoria de Arquitetura", app="Landing Zone em Nuvem",
         test_type="infra", test_model="whitebox", environment="production", origin="Migração para nuvem", sent=None, days=14,
         statuses=["draft"] * 6, failed_send=True),
    dict(name="Avaliação de Conscientização T4", client="Diretoria de Pessoas", app="Programa de Conscientização",
         test_type="infra", test_model="blackbox", environment="production", origin="Calendário anual", sent=None, days=8,
         statuses=["draft"] * 5),
    dict(name="Avaliação do Portal do Fornecedor", client="Diretoria de Suprimentos", app="Portal do Fornecedor",
         test_type="web", test_model="graybox", environment="staging", origin="Pedido da área", sent=None, days=4,
         statuses=["draft"] * 3),
]

# Standalone findings: one group per lifecycle state, with days since it was registered.
STANDALONE = [
    ("Sistema de Cobrança", "draft", 2), ("Intranet", "draft", 3),
    ("Sistema de Cobrança", "ready", 6), ("Portal de RH", "ready", 9),
    ("Portal de RH", "sent", 14), ("Intranet", "sent", 18),
    ("Plataforma de Dados", "fixing", 35), ("Sistema de Cobrança", "fixing", 48),
    ("Plataforma de Dados", "retesting", 60), ("Intranet", "retesting", 70),
    ("Portal de RH", "fixed", 90), ("Plataforma de Dados", "fixed", 110),
    ("Intranet", "risk_accepted", 40),
]

# Why the defense team assumed a risk instead of fixing it (D17).
RISK_REASONS = [
    "O sistema será descontinuado no próximo trimestre e o acesso já está restrito à rede interna.",
    "Há controle compensatório em vigor (monitoramento e bloqueio na borda); a correção exige troca do fornecedor.",
    "Risco aceito pela área de negócio após análise de impacto, com revisão prevista em seis meses.",
]

EXECUTIVE = [
    "A pedido de **$client**, o Red Team avaliou **$app** entre $start e $end. Foram registradas **$count** vulnerabilidades, das quais **$high** têm severidade alta ou crítica.",
    "De modo geral, os controles básicos estão presentes, mas sua aplicação não é uniforme. Os principais riscos vêm da falta de componentes centralizados, e não de erros isolados, e por isso a recomendação é priorizar correções estruturais.",
    "Recomendamos que a área responsável registre um plano de ação para cada item, começando pelos de maior severidade, e solicite o reteste assim que as correções forem concluídas.",
]

INTRODUCTION = [
    "Este relatório apresenta o resultado da avaliação de segurança de **$app**, conduzida pelo Red Team a partir do escopo aprovado por **$client**.",
    "O objetivo foi medir a eficácia dos controles existentes e apoiar a priorização de investimentos em segurança. O documento é confidencial e deve circular apenas entre as pessoas envolvidas na correção.",
    "A severidade de cada item segue o padrão CVSS 3.1, ajustado pela criticidade do ativo quando aplicável.",
]

SECTIONS = [
    ("Metodologia", "A avaliação seguiu quatro etapas:\n\n1. **Planejamento:** definição de escopo, janelas e contatos.\n2. **Reconhecimento:** levantamento dos ativos autorizados.\n3. **Avaliação:** verificação dos controles em janela acordada.\n4. **Relato:** consolidação dos resultados e reunião de encerramento."),
    ("Limitações", "A avaliação representa o estado do ambiente no período indicado. Sistemas fora do escopo não foram avaliados, e novas entregas podem alterar as conclusões.\n\n- Janela de teste restrita ao horário acordado.\n- Nenhum teste de indisponibilidade foi realizado."),
    ("Recomendações estratégicas", "- Definir um responsável por controle transversal.\n- Incluir requisitos de segurança nos critérios de aceite.\n- Medir o tempo de correção por severidade.\n- Repetir a avaliação após as correções estruturais."),
]

TEMPLATES = [
    ("Avaliação de aplicação web", "shared"),
    ("Avaliação de infraestrutura", "shared"),
    ("Avaliação de aplicativo móvel", "pending"),
    ("Modelo pessoal resumido", "private"),
]


# Dashboards (D18): name, description, variables, [(screen title, [(query, width in columns)])].
DASHBOARDS = [
    ("Remediação", "Para a TV da sala: só status, severidade e fonte.", [("aberta", "sent,fixing,retesting")], [
        ("Situação atual", [
            ('count where status:$aberta title "Abertas"', 1),
            ('count where status:$aberta cvss:9 title "Críticas abertas"', 1),
            ('count where status:sent -sent:15d title "Aguardando aceite há mais de 15 dias"', 1),
            ('count by severity where status:$aberta title "Abertas por severidade"', 1),
            ('count by status where status:$aberta title "Em andamento"', 2),
        ]),
        ("Correções", [
            ('count by severity over fixed per month where fixed:6m as bar title "Corrigidas por mês"', 3),
            ('median days sent..fixed where fixed:90d title "Mediana de dias até a correção (90 dias)"', 1),
            ('count by source where status:$aberta title "Abertas por fonte"', 2),
        ]),
    ]),
    ("Trimestre", "Para o relatório trimestral.", [("periodo", "3m"), ("aberta", "sent,fixing,retesting")], [
        ("Resumo", [
            ('count where sent:$periodo title "Enviadas no período"', 1),
            ('count where fixed:$periodo title "Corrigidas no período"', 1),
            ('median days sent..fixed where fixed:$periodo title "Mediana de dias até a correção"', 1),
            ('count by report, severity top 6 where status:$aberta as hbar title "Abertas por relatório"', 3),
        ]),
        ("Detalhes", [
            ('median days sent..fixed by severity where fixed:1y as table title "Dias até a correção, por severidade (12 meses)"', 2),
            ('count by operator where created:$periodo title "Encontradas por operador"', 1),
            ('count by severity, status where -status:draft -status:ready as table title "Severidade × status"', 3),
        ]),
    ]),
]
