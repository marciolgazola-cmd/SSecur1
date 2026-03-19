# Seguranca Atual e Lacunas

## Resumo executivo

O projeto ja possui conceitos importantes de seguranca funcional, como autenticacao, papeis, escopo por tenant e permissoes por recurso. Ainda assim, o estado atual nao deve ser tratado como pronto para producao sem endurecimento.

## Controles existentes no codigo

- autenticacao local por email/senha;
- separacao logica por `tenant_id`;
- papeis como `admin`, `editor`, `viewer` e templates adicionais;
- permissoes funcionais e visuais por recurso;
- escopo de conta (`smartlab` ou cliente) no usuario.

## Riscos relevantes identificados

### Senha em texto puro

O campo `users.password` armazena senha sem hash no banco atual.

Exemplo real encontrado no banco:

```text
admin@smartlab.com -> admin123
```

Isso e um risco critico. O minimo aceitavel para producao seria `argon2` ou `bcrypt` com politica de rotacao e reset seguro.

### Seed inseguro conhecido

O sistema recria o usuario seed com credencial previsivel quando o banco inicia vazio:

- `admin@smartlab.com`
- `admin123`

Essa credencial precisa ser eliminada ou forcar troca imediata no primeiro boot.

### Integridade referencial parcial

Nem todos os relacionamentos semanticamente importantes estao protegidos por FK. Exemplos:

- `permission_boxes.user_email` depende de email textual, nao de `users.id`;
- `users.role` e textual e nao referencia `roles.id`;
- varios campos JSON em `TEXT` aceitam qualquer conteudo sem validacao estrutural no banco.

### Ausencia de trilha formal de migracoes

Hoje o projeto usa `create_all()` e `ALTER TABLE` incrementais em runtime. Isso ajuda no bootstrap, mas nao substitui governanca de schema.

### Ausencia de endurecimento web

Nao ha, no repositorio atual, evidencias documentadas de:

- CSRF hardening;
- rate limit;
- auditoria estruturada persistente;
- politica de sessao robusta;
- MFA;
- SSO corporativo;
- segregacao de segredos por ambiente.

## Recomendacoes prioritarias

1. hash de senha imediato;
2. remocao da seed insegura em ambientes nao locais;
3. migracoes com Alembic;
4. auditoria de acessos e alteracoes;
5. revisao completa do modelo multi-tenant;
6. migracao para banco gerenciado em producao;
7. externalizacao de segredos e configuracoes sensiveis.

## Escopo da documentacao

Este documento registra o estado atual observado no codigo e no banco local em 2026-03-18. Ele nao deve ser interpretado como declaracao de conformidade ou prontidao de publicacao.
