<!-- page: dashboards -->
# Dashboards

Um dashboard responde a perguntas sobre o conjunto das vulnerabilidades: quantas estão abertas, quantas foram corrigidas por mês, quanto tempo a defesa leva para aceitar um achado. Ele é feito de gráficos, e cada gráfico é descrito por **uma linha de texto**, a consulta, que diz o que contar, como agrupar e como desenhar.

Os números de um dashboard são sempre **contagens e tempos**. Nenhum gráfico mostra uma vulnerabilidade, um identificador ou um host, e é por isso que um dashboard pode ser visto por quem não acessa as vulnerabilidades em si, como as contas do papel Dashboards, ou ficar exposto numa TV.

## A lista e o editor

Os dashboards ficam no menu, em **Dashboards**. A lista é compartilhada entre os administradores e as contas Dashboards: todos veem e editam os mesmos dashboards. **Editar** abre o editor, com o nome do dashboard, as suas [variáveis](#dash-variaveis) e as consultas. Cada consulta tem uma prévia ao lado, que se atualiza enquanto você escreve, então você vê o gráfico tomar forma antes de salvar. Um dashboard com uma consulta errada não é salvo: a mensagem diz o que está errado e em que ponto da linha.

## Telas

Um dashboard pode ter várias **telas**, cada uma com os seus gráficos e um título opcional, para separar assuntos: uma tela para o que está aberto, outra para os tempos de correção. Na página do dashboard, **Anterior** e **Próxima**, ou as setas ← e → do teclado, passam de uma tela para outra, e o endereço guarda a tela em que você está, como em `?tela=2`.

## Atualização

Os números são recalculados de tempos em tempos. No editor, **Atualizar os números a cada** define esse intervalo, de 30 segundos a 1 hora, para a página e para a TV, e **Na TV, trocar de tela a cada** define quanto tempo a TV mostra cada tela, de 5 segundos a 10 minutos. Na página, **Atualizar** recalcula na hora.

<!-- page: dash-consultas -->
# Escrevendo consultas

Uma consulta é uma frase curta, em inglês, com uma forma fixa:

```
<medida> [by <grupo>[, <grupo>]] [over <data> per <unidade>] [where <filtro>] [top N] [as <gráfico>] [title "…"]
```

Só a medida é obrigatória. As outras partes podem vir em qualquer ordem, cada uma no máximo uma vez. Vamos construir uma consulta aos poucos, para ver o que cada parte faz.

## A medida

A consulta mais simples é `count`: um número, com quantas vulnerabilidades existem. Em vez de contar, a medida também pode ser um tempo entre duas datas da mesma vulnerabilidade. `median days sent..fixed` é a mediana, em dias, entre o envio e a correção. Além de `median`, valem `avg`, `min`, `max` e percentis como `p90`. Um tempo calculado a partir de menos de três vulnerabilidades aparece como "—", porque um número assim diria pouco.

As datas que uma medida de tempo pode usar são as mesmas dos filtros: `created`, `updated`, `sent`, `accepted`, `fixing`, `retesting`, `fixed` e `risk`.

## Filtrando com where

`where` restringe o que é contado, com o **mesmo filtro da página Operações**. `count where status:sent,fixing,retesting` conta as vulnerabilidades abertas; a vírgula em `status:` quer dizer "um ou outro". Há uma diferença em relação às Operações: lá, um filtro que não dá para ler é ignorado, e aqui ele é um erro, porque um gráfico calculado sobre o filtro errado mostraria um número errado sem aviso.

## Agrupando com by

`by` divide a contagem em grupos. `count by severity where status:sent,fixing,retesting` mostra as abertas por severidade. Os grupos possíveis são `status`, `severity`, `source`, `report` e `operator`. A severidade vem do CVSS: crítica a partir de 9, alta a partir de 7, média a partir de 4 e baixa acima de 0. Com dois grupos, como em `by report, severity`, as barras ficam empilhadas, ou o resultado vira uma tabela cruzada.

Quando há muitos grupos, `top 6` mostra os seis maiores do primeiro `by` e soma o resto em "Outros".

## Ao longo do tempo com over

`over` cria um eixo de tempo: `count over fixed per month` conta as vulnerabilidades corrigidas em cada mês. As unidades são `day`, `week`, `month`, `quarter`, `semester` e `year`. O período do eixo é o do filtro sobre a mesma data, então `count over fixed per month where fixed:12m` mostra os últimos doze meses. O eixo sempre começa numa unidade inteira, como um mês, uma semana, um trimestre ou um semestre completos.

## A aparência

`as` escolhe o tipo do gráfico: `number`, `bar`, `hbar` (barras horizontais), `line` ou `table`. Sem `as`, o portal escolhe o que combina com a consulta. Por fim, `title "Abertas"` dá um título ao gráfico.

<!-- page: dash-exemplos -->
# Exemplos

Ver consultas prontas é o jeito mais rápido de pegar a linguagem. Os exemplos desta página vão do mais simples ao mais elaborado, e todos podem ser colados no editor e ajustados.

Um número grande, com o total de vulnerabilidades abertas, é um bom começo para qualquer dashboard:

```
count where status:sent,fixing,retesting title "Abertas"
```

Combinando um status com um filtro de data invertido, o número passa a vigiar um problema: as vulnerabilidades enviadas há mais de quinze dias que a defesa ainda não aceitou.

```
count where status:sent -sent:15d title "Aguardando aceite há mais de 15 dias"
```

Para ver como as abertas se distribuem, agrupe por severidade. Para ver quais relatórios concentram mais problemas, agrupe por relatório e severidade, mostrando os seis maiores em barras horizontais:

```
count by severity where status:sent,fixing,retesting
count by report, severity top 6 where status:sent,fixing,retesting as hbar
```

Com `over`, a pergunta passa a ser sobre o ritmo. O primeiro gráfico abaixo mostra quantas vulnerabilidades foram corrigidas em cada um dos últimos doze meses, por severidade, e o segundo compara os semestres pelo número de envios:

```
count by severity over fixed per month where fixed:12m as bar title "Corrigidas por mês"
count by severity over sent per semester where sent:25S2..26S2 as bar title "Enviadas por semestre"
```

As medidas de tempo respondem a quanto as coisas demoram. A primeira consulta abaixo mostra, numa tabela, a mediana de dias entre o envio e a correção para cada severidade, no último ano. A segunda mostra em quantos dias nove de cada dez vulnerabilidades enviadas foram aceitas, trimestre a trimestre:

```
median days sent..fixed by severity where fixed:1y as table
p90 days sent..accepted over sent per quarter
```

Por fim, um número fechado num período, útil para um balanço semestral:

```
count where sent:26S1 title "Enviadas em 26S1"
```

<!-- page: dash-variaveis -->
# Variáveis

Algumas partes de uma consulta se repetem em vários gráficos, ou mudam com frequência. A lista de status que conta como "aberta" aparece em quase todo dashboard, e o período que interessa pode ser o último trimestre hoje e o último ano amanhã. Uma **variável** guarda um trecho assim, para que ele seja escrito uma vez só.

Crie a variável no editor, com um nome e um valor, como `aberta` com o valor `sent,fixing,retesting`, ou `periodo` com o valor `3m`. Depois, escreva `$nome` na consulta:

```
count where status:$aberta fixed:$periodo
```

O valor entra no lugar de `$nome` antes de a consulta ser lida, inclusive dentro do título. Na página do dashboard, quem o vê pode mudar os valores e clicar em **Aplicar**, e a mudança vale só para aquela visualização. Para mudar o valor de vez, edite o dashboard.

<!-- page: dash-tv -->
# Links de TV

Um dashboard pode ficar exposto numa TV da sala sem que ninguém precise fazer login nela. Na página do dashboard, **Novo link de TV** cria um endereço que mostra o dashboard em tela cheia, com fundo escuro e sem login. Abra esse endereço no navegador da TV: ela passa pelas telas em sequência e recalcula os números nos intervalos definidos no dashboard. Uma mudança feita no dashboard chega à TV na atualização seguinte.

O link aparece uma única vez, logo depois de criado, então copie-o na hora. Se o perder, crie outro e revogue o antigo.

## O que a TV pode mostrar

Uma TV fica num lugar por onde passam pessoas que não necessariamente têm acesso ao portal, e por isso um link de TV é mais restrito que o dashboard. Ele só aceita agrupamentos por **status**, **severidade** e **fonte**: nenhum nome de relatório ou de pessoa chega à TV. O editor avisa quais consultas ficam de fora, e um gráfico que deixa de ser aceito depois de o link existir aparece na TV como indisponível. A TV também não recebe as consultas nem as variáveis, apenas os números e os títulos.

## Desligar um link

**Revogar** desliga o link na hora. Ele também para de funcionar se o dashboard for excluído ou se quem o criou perder o acesso. A criação e a revogação de links ficam nos logs de auditoria, e a lista de links mostra quando cada um foi aberto pela última vez.
