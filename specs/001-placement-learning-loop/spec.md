# Feature Specification: Nivelamento e Loop de Aprendizagem (Placement & Learning Loop)

**Feature Branch**: `001-placement-learning-loop`

**Created**: 2026-08-11

**Status**: Draft — aguardando aprovação (Constitution §2: nenhuma implementação pode começar sem spec aprovada)

**Spec Version**: 0.1.0

**Constitution Ref**: v2.1.0

**Input**: User description: "Especificação do produto inicial do LingoAI: uma plataforma onde o estudante aprende inglês de forma progressiva, conversando com um agente de IA por texto ou áudio, e praticando escrita, fala e audição. Cobre a primeira fatia vertical do produto — Nivelamento (placement test) + Loop de Conversação/Exercícios básico — com arquitetura, banco de dados, requisitos funcionais e não funcionais, critérios de aceite, impacto técnico, estratégia de testes e considerações de rollback completos, alinhados à LingoAI Constitution v2.1.0."

---

## 0. Contexto e Alinhamento com a Constitution

Esta especificação define o produto inicial do LingoAI: uma plataforma onde o estudante aprende inglês de forma progressiva, conversando com um agente de IA por texto ou áudio, e praticando escrita, fala e audição. Múltiplos agentes de IA especializados colaboram nos bastidores para personalizar a jornada — mas, conforme Constitution §1, a IA assiste o processo pedagógico; ela não define sozinha as decisões de progressão do usuário (essas decisões nascem de regras de domínio explícitas, informadas por dados que os agentes produzem).

Esta spec cobre apenas a primeira fatia vertical do produto: Nivelamento + Loop de Conversação/Exercícios básico, mas já especifica a arquitetura e o banco de dados completos, para que features futuras (fala, novos agentes, mobile) sejam extensões e não retrabalho (Constitution §4, §7, §17).

## Clarifications

### Session 2026-08-11

- Q: Que elementos de gamificação devem existir nesta iteração para a avaliação de progressão do estudante? → A: Moderado — sistema de XP por atividade concluída, streak diário e badges de marcos pedagógicos, sem leaderboard/comparação social entre estudantes.
- Q: Se o desempenho do estudante cair, o `LearnerProfile` pode regredir de nível? → A: Não — o nível nunca regride automaticamente; desempenho fraco aciona mais prática/reforço na mesma faixa, não perda de nível.
- Q: Onde o estudante vê o feedback gamificado de progressão (XP/streak/badges)? → A: Feedback inline imediato após cada atividade, complementado por um painel de progresso persistente para consulta a qualquer momento.
- Q: O que dispara o avanço de nível de uma habilidade? → A: Taxa de acerto sustentada numa janela recente de atividades (ex.: ≥80% nas últimas N atividades) — um erro isolado não reinicia o progresso; valor exato do limiar/janela fica para o Technical Plan.
- Q: Se o estudante perder um dia sem completar nenhuma atividade, o streak zera ou existe tolerância? → A: Reset imediato — perder um dia sem atividade zera o streak, sem mecanismo de congelamento/tolerância nesta iteração.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Nivelamento inicial do estudante (Priority: P1)

Um novo estudante cria sua conta e é imediatamente guiado por uma conversa de nivelamento conduzida por IA, que avalia seu inglês (vocabulário, gramática, compreensão escrita e, quando houver áudio, pronúncia/compreensão oral) e gera um perfil de nível por habilidade (leitura, escrita, fala, audição).

**Why this priority**: Sem nivelamento não há personalização possível — é a fundação de todo o produto. Um estudante que não sabe seu nível real, ou recebe conteúdo genérico, abandona a plataforma. Esta é a menor fatia que já entrega valor sozinha: mesmo sem o loop de aprendizagem completo, saber seu nível real já é útil.

**Independent Test**: Pode ser testado de ponta a ponta criando uma conta nova, completando a conversa de nivelamento em texto, e verificando que um resultado de nível por habilidade é gerado e exibido ao estudante — sem depender de nenhuma outra funcionalidade do loop de aprendizagem.

**Acceptance Scenarios**:

1. **Given** um visitante sem conta, **When** ele se cadastra com e-mail/senha, **Then** o fluxo de nivelamento inicia automaticamente no primeiro acesso.
2. **Given** um estudante em nivelamento, **When** ele responde às perguntas em texto conduzidas pelo agente de IA, **Then** ao final o sistema gera e persiste um nível estimado separado por habilidade (leitura, escrita, fala, audição).
3. **Given** um nivelamento concluído, **When** o estudante acessa o resumo, **Then** ele vê seu nível estimado e pontos fortes/fracos identificados.
4. **Given** um ambiente onde entrada de áudio está disponível, **When** o estudante responde por fala durante o nivelamento, **Then** essa resposta também é avaliada como parte do nivelamento.

---

### User Story 2 - Loop de aprendizagem com feedback e progressão (Priority: P2)

Após o nivelamento, o estudante entra em um ciclo contínuo de conversação guiada e exercícios de escrita/fala/audição adequados ao seu nível. Cada resposta gera feedback pedagógico explicativo (não apenas certo/errado) e é registrada como evento de aprendizagem, que alimenta uma regra de domínio auditável responsável por decidir a próxima atividade/nível.

**Why this priority**: É o motivo do estudante voltar todos os dias — o nivelamento (P1) entrega um diagnóstico único, mas é este loop que entrega aprendizado contínuo e evolução mensurável. Depende do nivelamento (P1) já existir para saber o ponto de partida.

**Independent Test**: Com um estudante já nivelado (perfil pré-existente), pode ser testado completando uma atividade (conversa ou exercício), verificando que: (a) a atividade oferecida é compatível com o nível do estudante, (b) o feedback recebido explica o erro/acerto, e (c) um evento de aprendizagem imutável foi registrado e é possível derivar dele por que o estudante permanece ou avança de nível.

**Acceptance Scenarios**:

1. **Given** um estudante recém-nivelado, **When** ele acessa a plataforma, **Then** o sistema apresenta pelo menos uma atividade (conversação ou exercício) consistente com o nível detectado.
2. **Given** um estudante respondendo a um exercício, **When** ele envia sua resposta, **Then** recebe feedback pedagógico textual explicando o que estava certo/errado e como corrigir — não apenas uma pontuação.
3. **Given** uma sequência de eventos de aprendizagem de um estudante, **When** alguém consulta por que ele está no nível atual, **Then** a explicação é reconstruível a partir de uma regra de domínio testável, e não apenas "a IA decidiu assim".
4. **Given** uma conversa em andamento com o agente de conversação, **When** o estudante envia uma mensagem, **Then** recebe uma resposta adaptada ao seu nível corrente em tempo hábil para manter o ritmo da conversa.
5. **Given** um estudante que acabou de concluir uma atividade, **When** o resultado é processado, **Then** ele vê imediatamente, na mesma tela, o XP ganho, o streak atualizado e qualquer badge desbloqueado, e pode consultar esse mesmo progresso depois em um painel dedicado.

---

### User Story 3 - Plataforma extensível (múltiplos agentes, multimodal, multi-provedor) (Priority: P3)

A arquitetura de bastidores comprova, já nesta primeira fatia, que suporta múltiplos agentes de IA especializados colaborando, que o provedor de IA por trás de cada agente pode ser trocado sem afetar o comportamento percebido pelo estudante, e que a futura ativação de entrada/saída por áudio não vai exigir retrabalho das regras de negócio já construídas.

**Why this priority**: Não é uma jornada visível ao estudante final nesta iteração, mas é uma condição estrutural exigida pela Constitution (§4, §5, §6) para que as próximas fatias (fala ativada, novos agentes, cliente mobile) sejam extensões e não reescritas. Prioridade P3 porque o produto funciona (P1+P2) mesmo antes desta capacidade ser exercitada, mas ela precisa existir desde o início para não travar o roadmap.

**Independent Test**: Pode ser verificado trocando a configuração do provedor de IA usado pelo agente de conversação e confirmando que o comportamento observável pelo estudante não muda; e verificando que as interfaces de entrada/saída de áudio existem e são chamadas pela camada de conversação mesmo que a implementação real de fala não esteja ligada nesta iteração.

**Acceptance Scenarios**:

1. **Given** o sistema configurado com um provedor de IA para o agente de conversação, **When** a configuração desse provedor é trocada por outro, **Then** o comportamento percebido pelo estudante permanece consistente, sem alteração de código de domínio.
2. **Given** a arquitetura de agentes especializados (nivelamento, conversação, progressão), **When** cada agente é testado isoladamente, **Then** cada um pode ser validado sem depender da implementação real de IA de um provedor específico.
3. **Given** que o primeiro release entrega apenas texto, **When** a capacidade de áudio for ativada em uma fatia futura, **Then** nenhuma regra de domínio precisa mudar — apenas a implementação concreta por trás da interface de entrada/saída de áudio.

---

### Edge Cases

- O que acontece se o estudante abandonar o nivelamento antes de concluir (fecha a aba, perde conexão)? O sistema deve permitir retomar de onde parou ou reiniciar de forma clara, sem deixar o estudante em um estado indefinido.
- O que acontece se a resposta do provedor de IA demorar além do esperado ou falhar durante uma conversa? O estudante deve receber um retorno claro (erro amigável / nova tentativa), sem travar a sessão nem perder o progresso já registrado.
- O que acontece se o estudante não tiver microfone disponível ou áudio não for suportado no navegador durante o nivelamento? O nivelamento deve continuar funcionando apenas por texto, sem bloquear o fluxo.
- O que acontece se um sinal de avaliação do agente de IA for ambíguo ou conflitante para uma decisão de progressão? A regra de domínio de progressão deve ter um comportamento padrão definido (ex.: manter nível atual) em vez de propagar a ambiguidade como decisão arbitrária.
- O que acontece se um estudante tentar pular diretamente para o loop de aprendizagem sem completar o nivelamento? O sistema deve impedir ou aplicar um nível padrão explícito e sinalizado como não verificado.
- O que acontece se dois eventos de aprendizagem chegarem para a mesma atividade em rápida sucessão (ex.: duplo envio)? O evento deve ser tratado de forma idempotente, sem duplicar o efeito sobre o perfil do estudante.
- O que acontece se um estudante tiver desempenho consistentemente fraco em um nível? O sistema não rebaixa o nível automaticamente (FR-9); em vez disso, direciona mais atividades de reforço na mesma faixa até o desempenho melhorar.

## Requirements *(mandatory)*

### Functional Requirements

**Onboarding e Nivelamento**

- **FR-1**: O sistema DEVE permitir criação de conta (e-mail/senha no MVP; a arquitetura de autenticação DEVE permitir adicionar OAuth futuramente sem quebrar contratos existentes).
- **FR-2**: Ao primeiro acesso, o sistema DEVE iniciar automaticamente um fluxo de Nivelamento conduzido pelo Assessment/Leveling Agent.
- **FR-3**: O Nivelamento DEVE aceitar entrada por texto e, quando disponível, por áudio (fala), avaliando ao menos: vocabulário, gramática, compreensão escrita e (quando houver áudio) pronúncia/compreensão oral básica.
- **FR-4**: Ao final do Nivelamento, o sistema DEVE gerar um Perfil de Nivelamento persistente com nível estimado por habilidade (leitura, escrita, fala, audição — não apenas um nível único global), que serve de ponto de partida da trilha de aprendizagem.
- **FR-5**: O estudante DEVE poder visualizar um resumo do resultado do nivelamento (nível estimado, pontos fortes/fracos).

**Loop de Aprendizagem**

- **FR-6**: O sistema DEVE oferecer uma conversa contínua com o Conversation Agent, adaptada ao nível corrente do estudante.
- **FR-7**: O sistema DEVE gerar exercícios de escrita, fala e audição consistentes com o nível e os gaps identificados no Perfil de Nivelamento.
- **FR-8**: Cada exercício DEVE gerar feedback pedagógico (não apenas certo/errado), explicando o erro e sugerindo correção.
- **FR-9**: O Progression Agent (ou motor de domínio equivalente) DEVE decidir a próxima atividade/nível com base em regras de domínio explícitas alimentadas pelos eventos de aprendizagem — a IA generativa fornece sinais (ex.: avaliação de uma resposta aberta), mas a decisão de progressão em si é uma regra de domínio auditável, não uma decisão opaca do LLM. O avanço de nível numa habilidade DEVE ser disparado por uma taxa de acerto sustentada numa janela das atividades mais recentes daquela habilidade (ex.: acerto igual ou acima de um limiar definido nas últimas N atividades) — não por uma sequência ininterrupta sem erros; um erro isolado dentro da janela não reinicia o progresso. O valor exato do limiar e do tamanho da janela é decisão do Technical Plan. O nível do estudante em cada habilidade NUNCA regride automaticamente: desempenho fraco sustentado DEVE acionar mais atividades de reforço na mesma faixa de nível, nunca um rebaixamento de nível.
- **FR-10**: O sistema DEVE registrar cada interação relevante (resposta, correção, tempo gasto, tentativa) como um evento de aprendizagem imutável.

**Gamificação da Progressão**

- **FR-15**: O sistema DEVE conceder pontos de experiência (XP) ao estudante por cada atividade concluída (conversação ou exercício), com o valor de XP influenciado pelo desempenho registrado no `LearningEvent` correspondente.
- **FR-16**: O sistema DEVE manter uma contagem de streak (sequência de dias consecutivos com pelo menos uma atividade concluída), visível ao estudante. O streak DEVE reiniciar para zero caso o estudante não conclua nenhuma atividade em um dia; não há mecanismo de tolerância/congelamento nesta iteração.
- **FR-17**: O sistema DEVE conceder badges (selos) ao estudante ao atingir marcos pedagógicos definidos (ex.: primeira conversa concluída, primeiro nível avançado, streak de 7 dias), exibidos no perfil do estudante.
- **FR-18**: XP, streak e badges são reforço motivacional e DEVEM ser derivados dos mesmos `LearningEvent` que alimentam a decisão de progressão (Constitution §12) — não constituem fonte de verdade paralela nem substituem a regra de domínio de progressão (FR-9). Comparação social entre estudantes (leaderboard/ranking) está fora do escopo desta iteração.
- **FR-19**: O sistema DEVE exibir o ganho de XP, a atualização de streak e qualquer badge desbloqueado imediatamente após a conclusão de uma atividade (feedback inline), e DEVE também disponibilizar um painel de progresso persistente onde o estudante pode consultar XP total, streak atual e badges conquistados a qualquer momento.

**Múltiplos Agentes**

- **FR-11**: A arquitetura DEVE suportar múltiplos agentes de IA especializados operando de forma colaborativa, cada um com responsabilidade única, input e output explícitos. Nesta iteração, no mínimo:
  - Assessment/Leveling Agent — conduz e avalia o nivelamento.
  - Conversation Agent — conduz o diálogo pedagógico contínuo.
  - Progression/Orchestrator Agent — decide a próxima atividade e consolida sinais dos demais agentes em decisões de progressão.
- **FR-12**: Cada agente DEVE ser testável de forma independente, com contratos de entrada/saída bem definidos, sem acoplamento a um provedor de IA específico.

**Multimodalidade (texto/áudio)**

- **FR-13**: O sistema DEVE suportar entrada e saída em texto desde o primeiro release.
- **FR-14**: O sistema DEVE suportar entrada de áudio (fala do estudante → texto) e saída em áudio (texto → fala) como capacidade de plataforma, isolada atrás de uma interface (ex.: provedor de reconhecimento de fala / provedor de síntese de fala), mesmo que o primeiro release entregue apenas texto e uma segunda fatia ligue o áudio — sem exigir mudança nas regras de domínio.

### Non-Functional Requirements

- **NFR-1 (Local-First)**: A aplicação completa (frontend, backend, banco de dados, orquestração de agentes) DEVE rodar localmente via Docker Compose, sem dependência de nuvem, exceto pela chamada aos provedores de IA externos (que devem ser abstraídos e, quando possível, ter fallback local/mock para desenvolvimento).
- **NFR-2 (Portabilidade)**: Nenhuma regra de negócio DEVE depender de recurso proprietário de um provedor de nuvem ou de um provedor de IA específico.
- **NFR-3 (Configuração)**: Toda configuração sensível (chaves de API de provedores de IA/STT/TTS, credenciais de banco) DEVE vir de variáveis de ambiente / secret manager, nunca hardcoded.
- **NFR-4 (Observabilidade mínima)**: Toda chamada a um agente de IA DEVE gerar log estruturado (agente, input resumido, latência, sucesso/erro), sem registrar dados sensíveis desnecessários.
- **NFR-5 (Desempenho)**: O turno de conversa (mensagem do aluno → resposta do Conversation Agent) DEVE responder em até ~3s em ambiente local com provedor de IA padrão, para não quebrar a experiência de conversação.
- **NFR-6 (Privacidade/Segurança)**: Dados de aprendizagem e áudio do estudante são dados pessoais sensíveis; DEVEM ser protegidos por autenticação, autorização e criptografia em trânsito.
- **NFR-7 (Testabilidade)**: Toda regra de progressão e todo agente DEVEM ser cobertos por testes automatizados determinísticos — chamadas reais a LLM DEVEM ser mockadas/gravadas (cassette/fixture) nos testes, para reprodutibilidade.
- **NFR-8 (Extensibilidade de cliente)**: A API pública DEVE ser desenhada para que um futuro client mobile consuma os mesmos contratos sem alterar regras de domínio.

### Key Entities *(include if feature involves data)*

- **User**: Conta do estudante — credenciais, preferências de idioma nativo, timezone.
- **PlacementSession**: Uma sessão de nivelamento (status, início, conclusão).
- **PlacementResult**: Resultado do nivelamento — nível estimado por habilidade (leitura, escrita, fala, audição), gerado ao final de uma `PlacementSession`.
- **LearnerProfile**: Projeção do nível atual do estudante por habilidade e trilha ativa; derivada a partir do histórico de `LearningEvent`, incluindo a taxa de acerto na janela recente de atividades usada para decidir avanço de nível — não é a fonte primária da verdade.
- **LearningPath / Unit / Activity**: Estrutura pedagógica — unidades e atividades disponíveis por nível/habilidade, usadas para sequenciar o loop de aprendizagem.
- **ConversationSession / Message**: Uma conversa contínua com o Conversation Agent e suas mensagens (texto e, quando aplicável, referência a áudio).
- **LearningEvent**: Evento imutável de aprendizagem (tipo, payload, timestamp, referência a usuário/atividade/sessão) — fonte de verdade para reconstruir o progresso do estudante; toda decisão de progressão deve ser rastreável até uma sequência de eventos.
- **GamificationProfile**: Projeção do estado motivacional do estudante — XP total, streak atual (dias consecutivos) e badges conquistados; derivada do histórico de `LearningEvent`, da mesma forma que `LearnerProfile` (não é fonte primária).
- **Badge**: Catálogo de marcos gamificados disponíveis (nome, critério de concessão) e seus registros de concessão a estudantes.
- **AgentInvocationLog**: Registro de observabilidade de cada chamada a um agente de IA (agente, input resumido, output resumido, latência, provedor usado, sucesso/erro).

## Technology Choices *(mandatory per LingoAI Constitution §2, §6, §18)*

> A LingoAI Constitution exige que decisões de tecnologia sejam justificadas por requisitos do projeto (§6) e que "Technical Impact" faça parte da especificação (§2). Esta seção fixa apenas as escolhas de plataforma/arquitetura necessárias para que o restante da spec (dados, testes, rollback) seja concreto. Decisões de nível mais fino (provedor de IA específico, REST vs GraphQL, escala de nível exata, cache) são deliberadamente deixadas para o Technical Plan — ver "Assumptions" e a lista de perguntas em aberto ao final deste documento.

Regra geral: modular monolith no MVP, com fronteiras de módulo já desenhadas por bounded context (Onboarding/Nivelamento, Conversação, Progressão/Domínio de Aprendizagem, Agentes de IA, Identidade), para permitir extração futura em serviços somente se a demanda justificar.

| Camada | Escolha | Justificativa |
|---|---|---|
| Frontend | TypeScript + React (Next.js) | Ecossistema maduro para web; SSR/CSR híbrido facilita evoluir para PWA sem reescrita; boa disponibilidade de bibliotecas de UI/áudio (Web Audio API, MediaRecorder) nativas do browser. |
| Backend | Python + FastAPI | Ecossistema maduro e vendor-neutro para orquestração de agentes de IA, STT/TTS e processamento de linguagem; FastAPI é leve, tipado (Pydantic), performático, sem overengineering. |
| Arquitetura interna do backend | Clean Architecture + DDD, módulos por bounded context, dependências apontando para dentro | Alinhado à Constitution §3. |
| Orquestração de agentes | Camada própria de "AI Agents" isolada da infra, com interface por agente e adapters por provedor | Garante que provedores de IA sejam substituíveis sem afetar regras de negócio (Constitution §5). |
| Banco de dados (operacional) | PostgreSQL | Open-source, maduro, portável, forte suporte transacional; extensão pgvector cobre necessidades de embeddings sem introduzir um segundo banco no MVP. |
| Dados analíticos / eventos | Tabela(s) de eventos append-only no próprio PostgreSQL, desenhadas para futura migração a um data warehouse/stream se justificado | Evita introduzir um segundo sistema de dados antes de necessário, mas já separa dado operacional de analítico dentro do schema. |
| Migrações | Alembic | Padrão maduro para versionar schema do Postgres. |
| STT/TTS | Interface abstrata com implementação inicial substituível; provedor específico fica para o Technical Plan | Constitution §5, §6, §14. |
| Empacotamento local | Docker Compose (frontend, backend, Postgres, cache opcional) | Constitution §7. |
| API | Contrato explícito versionado (REST ou GraphQL, a decidir no Technical Plan), sem vazar detalhes internos de domínio | Constitution §14. |

## Acceptance Criteria *(mandatory)*

- **AC-1 — Nivelamento funcional**: Um novo usuário, ao se cadastrar, é automaticamente guiado por uma conversa de nivelamento em texto; ao final, um `PlacementResult` é persistido com nível por habilidade, visível para o usuário.
- **AC-2 — Loop pós-nivelamento**: Após o nivelamento, o sistema apresenta ao menos uma atividade (conversação ou exercício) consistente com o nível detectado, e a resposta do usuário gera pelo menos um `LearningEvent`.
- **AC-3 — Feedback pedagógico**: Toda resposta a um exercício retorna feedback textual explicando acerto/erro, não apenas um score.
- **AC-4 — Progressão auditável**: Dado o histórico de `LearningEvent` de um usuário, é possível reconstruir/justificar por que o `LearnerProfile` está no nível atual, via regra de domínio testável (não apenas "o LLM decidiu").
- **AC-5 — Local-first**: `docker compose up` sobe frontend, backend e banco localmente e permite completar o fluxo de nivelamento + uma atividade, sem qualquer dependência de infraestrutura cloud (exceto a chamada ao provedor de IA externo, se configurado).
- **AC-6 — Substituibilidade de provedor de IA**: É possível trocar o adapter do provedor de IA usado pelo Conversation Agent via configuração, sem alterar código de domínio ou dos demais agentes.
- **AC-7 — Áudio isolado por contrato**: Mesmo que o primeiro release não entregue STT/TTS ligados de ponta a ponta, as interfaces de entrada/saída de áudio existem e são consumidas pela camada de conversação, comprovando que a ativação futura do áudio não exige mudança de domínio.
- **AC-8 — Testes determinísticos**: A suíte de testes automatizados roda sem chamadas reais a provedores de IA (mockadas/fixture), com cobertura das regras críticas de progressão (unit) e do fluxo de nivelamento (integração/E2E).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um novo estudante consegue completar o cadastro e receber um nível estimado por habilidade em uma única sessão, sem assistência externa.
- **SC-002**: 100% das respostas do estudante a uma atividade de aprendizagem recebem, na mesma sessão, um feedback explicativo (não apenas certo/errado).
- **SC-003**: Para qualquer estudante, a justificativa do nível atual pode ser reconstruída a partir do seu histórico de atividade registrado, por meio de uma regra auditável — sem depender de explicação não documentada de um modelo de IA.
- **SC-004**: O fluxo completo guiado (cadastro → nivelamento → primeira atividade) é executável de ponta a ponta em ambiente local, sem nenhuma dependência de infraestrutura de nuvem além da chamada ao provedor de IA.
- **SC-005**: Uma resposta conversacional do sistema chega ao estudante em até ~3 segundos em condições normais de operação, preservando a fluidez da conversa.
- **SC-006**: O provedor de IA usado por trás da conversação pode ser substituído sem alteração perceptível no comportamento do produto para o estudante.
- **SC-007**: Após concluir qualquer atividade, o estudante vê imediatamente o XP ganho e o status atualizado do seu streak, sem precisar navegar para outra tela, e consegue revisitar esse mesmo progresso depois em um painel dedicado.

## Assumptions

- Autenticação inicial é e-mail/senha; OAuth é uma extensão futura e não bloqueia esta fatia.
- A escala de nível (ex.: CEFR A1–C2 completa ou uma escala interna própria) será finalizada no Technical Plan; esta spec assume apenas que o nível é reportado por habilidade (leitura, escrita, fala, audição), não como um único nível global.
- Nesta iteração, apenas 2–3 agentes são implementados (Assessment/Leveling, Conversation, Progression/Orchestrator); mais agentes especializados são extensões futuras permitidas pela arquitetura, não bloqueiam esta fatia.
- Entrada/saída de áudio é uma capacidade de plataforma preparada nesta iteração (contratos/interfaces existem), mas sua implementação real ponta a ponta pode ser entregue em uma fatia seguinte.
- Fora do escopo desta iteração, mas sem impedimento arquitetural futuro: aplicativo mobile nativo (PWA é aspiração futura), gamificação social/competitiva (leaderboard, ranking entre estudantes — ver Clarifications), turmas/professores humanos, idiomas de ensino além do inglês, e deploy em nuvem.
- REST vs GraphQL para a API pública, provedor(es) específico(s) de IA generativa e de STT/TTS, estratégia de cache/sessão (ex.: Redis), e a estrutura exata de módulos dentro do monolito são decisões deliberadamente deixadas para o Technical Plan — não bloqueiam a aprovação desta spec.

## Technical Impact

- Introduz um novo bounded context de Agentes de IA como camada própria (não é "infra" nem "domínio puro"): define contratos que o domínio usa via portas/interfaces, mas cuja implementação concreta (chamadas a LLM) fica isolada, respeitando Clean Architecture.
- Cria o schema inicial do PostgreSQL (Identidade, Nivelamento, Progressão, Conversação, Eventos, Log de Agentes) e a primeira migração via Alembic.
- Define o contrato de API pública (endpoints de auth, nivelamento, conversação, exercícios) que o client web consumirá — mobile futuro reaproveita o mesmo contrato.
- Estabelece o padrão de Docker Compose local que servirá de base para o pipeline de CI e, futuramente, para o deploy em nuvem.
- Não introduz microsserviços nem filas/streaming nesta fase — extração futura só se demanda medida justificar.

## Testing Strategy

Seguindo a pirâmide de testes (Constitution §11):

- **Unit tests (prioridade máxima)**:
  - Regras de domínio de progressão (Progression Agent/motor de regras): dado um conjunto de `LearningEvent`, o nível resultante é determinístico e testável sem qualquer chamada externa.
  - Regras de derivação do `PlacementResult` a partir das respostas do nivelamento.
  - Cada agente testado isoladamente com inputs/outputs mockados.
- **Integration tests**:
  - Fluxo API → domínio → banco (ex.: submeter resposta de exercício → `LearningEvent` persistido → projeção de `LearnerProfile` atualizada).
  - Adapters de provedor de IA testados contra fixtures/cassettes gravados (sem chamada real em CI).
- **End-to-End tests** (jornadas críticas, não detalhes de implementação):
  - Cadastro → Nivelamento completo → recebimento de `PlacementResult`.
  - Nivelamento concluído → primeira atividade recomendada → conclusão → evento registrado → profile atualizado.
- **Reprodutibilidade**: Nenhum teste automatizado depende de resposta não determinística de LLM real; todo teste que envolveria IA usa double/fixture.

## Rollback Considerations

- **Migrações de banco**: Toda migration Alembic desta iteração DEVE ter script de downgrade funcional, já que o schema de Nivelamento/Progressão é a base de tudo que vem depois.
- **Feature flag de Nivelamento**: O fluxo de nivelamento obrigatório no primeiro acesso DEVE poder ser desativado via configuração, permitindo reverter para um fluxo simplificado (ex.: nível default) sem deploy de código, caso o nivelamento apresente problema em produção.
- **Isolamento de provedor de IA**: Caso o provedor de IA configurado falhe ou precise ser revertido, a troca deve ser possível apenas via configuração (adapter), sem rollback de código de domínio.
- **Eventos são imutáveis e aditivos**: Como `LearningEvent` nunca é alterado/apagado, qualquer bug na lógica de progressão pode ser corrigido reprocessando os eventos existentes com a regra corrigida, sem perda de dado histórico.

## Perguntas em aberto para o Technical Plan

Estas decisões são deliberadamente deixadas para a fase de Technical Plan (Constitution §2), não para esta spec:

- Provedor(es) de IA generativa e de STT/TTS específicos.
- REST vs GraphQL para a API pública.
- Escala CEFR completa vs. escala interna própria para os níveis.
- Estratégia de cache/sessão (ex.: Redis) — só entra se justificado.
- Estrutura exata de módulos dentro do monolito (nomes de bounded contexts).
- Valor exato do limiar de taxa de acerto e do tamanho da janela de atividades recentes usados na regra de avanço de nível (FR-9), e a fórmula exata de conversão de desempenho em XP (FR-15).
