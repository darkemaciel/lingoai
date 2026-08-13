# LingoAI

Plataforma de ensino de idiomas guiada por IA: nivelamento inicial, loop de aprendizagem (conversação + exercícios) com feedback pedagógico, progressão por regra determinística e gamificação leve (XP, streak, badges).

Stack: Next.js 14 (TypeScript) no frontend, FastAPI (Python 3.12, Clean Architecture / modular monolith) no backend, PostgreSQL como único banco. Toda integração com IA (Anthropic / OpenAI / mock local) fica atrás de portas/adapters trocáveis — ver `specs/001-placement-learning-loop/`.

## Pré-requisitos

- Docker Desktop com WSL2 habilitado (Windows) — **requer virtualização (VT-x/AMD-V) ativada na BIOS/UEFI**. Sem isso o `docker compose up` falha ao iniciar o motor do WSL2.
- Alternativamente, para rodar sem Docker: Python 3.12 + [uv](https://docs.astral.sh/uv/), Node.js 20+, e um PostgreSQL 16 local.

## Subindo tudo com Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

- Backend: http://localhost:8000 (`GET /api/v1/health`, docs em `/docs`)
- Frontend: http://localhost:3000
- Postgres: `localhost:5432`

Na primeira vez, rode as migrações e (opcionalmente) os seeds de conteúdo/badges:

```bash
docker compose exec backend alembic upgrade head
docker compose exec backend python -m learning_content.infrastructure.seed
docker compose exec backend python -m gamification.infrastructure.seed
```

`.env` (`AI_PROVIDER=local` por padrão) usa o `LocalModelAdapter` determinístico — nenhuma chave de API é necessária para rodar a stack completa. Para usar um provedor real, defina `AI_PROVIDER=anthropic` ou `AI_PROVIDER=openai` e a respectiva chave (`ANTHROPIC_API_KEY`/`OPENAI_API_KEY`), e reinicie o backend.

## Rodando os testes

```bash
docker compose exec backend pytest
```

Sem Postgres acessível, os testes que dependem de banco são pulados automaticamente (`SKIPPED`) — os testes puramente unitários/de contrato (regras de domínio, adapters) continuam rodando normalmente fora do Docker:

```bash
cd backend
uv sync
uv run pytest
```

Frontend:

```bash
cd frontend
npm install
npm run lint
npm run build
npx playwright test   # E2E — requer a stack completa (docker compose up) rodando
```

## Estrutura do projeto

```text
backend/
  src/{identity,placement,conversation,progression,gamification,learning_content,ai_agents,shared_kernel}/
    domain/ application/ infrastructure/ api/      # Clean Architecture por módulo
  migrations/        # Alembic
  tests/{unit,integration,contract}/
frontend/
  src/app/            # Next.js app router (páginas + rotas BFF em src/app/api/)
  src/components/      # ex.: feedback de gamificação
  src/services/        # cliente de API tipado, sessão (cookies httpOnly)
  tests/{e2e}/          # Playwright
docker-compose.yml
specs/001-placement-learning-loop/   # spec, plano, contratos, tarefas
```

## Solução de problemas

**`docker compose up` falha / `docker ps` retorna erro 500 no pipe do Docker Desktop**: geralmente indica que o WSL2 não conseguiu iniciar por falta de virtualização habilitada. Verifique:

1. Reinicie o Docker Desktop.
2. Se persistir, rode `wsl --status` num PowerShell — se aparecer erro de virtualização, reinicie o computador, entre na BIOS/UEFI e habilite Intel VT-x / AMD-V.
3. Confirme o recurso opcional do Windows "Plataforma de Máquina Virtual" habilitado (`wsl --install --no-distribution` habilita automaticamente).

Sem isso, o Postgres não sobe e os testes de integração/E2E ficam bloqueados (skip automático), mas todo o resto do desenvolvimento (unit tests, contract tests, lint, build) funciona normalmente sem Docker.
