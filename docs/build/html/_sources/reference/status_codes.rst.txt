Códigos de Status dos Pedidos
==============================

Lista completa de todos os status possíveis para pedidos (``Orders.order_status``).

.. list-table:: Status de Pedidos
   :header-rows: 1
   :widths: 10 25 65

   * - Código
     - Nome
     - Descrição
   * - ``PR``
     - Processando
     - Estado inicial após importação. Pedido em análise.
   * - ``AS``
     - Atribuir SIM
     - Aguardando atribuição de um cartão SIM disponível no inventário.
   * - ``AI``
     - Atribuir IMEI
     - Aguardando associação de IMEI ao pedido (eSIM).
   * - ``AA``
     - Agd. Ativação
     - SIM atribuído; aguardando data de ativação para chamar a API da operadora.
   * - ``AO``
     - Agd. Operadora
     - Aguardando confirmação da operadora.
   * - ``AE``
     - Agd. Envio
     - Pedido físico aguardando envio (chip físico).
   * - ``AG``
     - Agência
     - Pedido a ser retirado em agência parceira.
   * - ``AT``
     - Ativado
     - SIM ativado com sucesso na operadora.
   * - ``EE``
     - Enviar E-mail
     - Ativação concluída; aguardando envio de e-mail de confirmação ao cliente.
   * - ``CN``
     - Concluído
     - Pedido encerrado com sucesso (e-mail enviado).
   * - ``CC``
     - Cancelado
     - Pedido cancelado. Estado final sem reversão.
   * - ``DA``
     - Data em Aberto
     - Data de ativação não definida pelo cliente.
   * - ``DE``
     - Desativado
     - SIM desativado pela operadora (expirado ou solicitado).
   * - ``EA``
     - Erro Ativação
     - Falha na chamada à API da operadora na tentativa de ativação.
   * - ``ED``
     - Erro Desativação
     - Falha na tentativa de desativação do SIM.
   * - ``EI``
     - Erro Importação
     - Falha ao importar dados do pedido do e-commerce.
   * - ``ES``
     - Em Separação
     - Pedido físico em processo de separação no estoque.
   * - ``MB``
     - Motoboy
     - Pedido físico saiu para entrega via motoboy.
   * - ``PV``
     - Plano de Voz
     - Pedido de chamada de voz — processado pelo app ``voice_calls``.
   * - ``RB``
     - Reembolsado
     - Reembolso total concluído.
   * - ``RE``
     - Reembolsar
     - Solicitação de reembolso total em processamento.
   * - ``RC``
     - Reembolso Parcial
     - Reembolso parcial concluído.
   * - ``RP``
     - Reprocessar
     - Pedido marcado para reprocessamento manual.
   * - ``RS``
     - Reuso
     - Pedido usando SIM reutilizado (condição ``reuso-sim``).
   * - ``RT``
     - Retirada
     - Pedido físico aguardando retirada pelo cliente.
   * - ``VS``
     - Verificar SIM
     - SIM requer verificação manual antes de ativação.

Status dos SIMs
===============

Status possíveis para ``Sims.sim_status``:

.. list-table:: Status de SIM
   :header-rows: 1
   :widths: 10 20 70

   * - Código
     - Nome
     - Descrição
   * - ``DS``
     - Disponível
     - SIM livre no inventário, pronto para ser atribuído a um pedido.
   * - ``AT``
     - Ativado
     - SIM ativo, associado a um pedido em andamento.
   * - ``DE``
     - Desativado
     - SIM foi desativado na operadora (plano expirado).
   * - ``CC``
     - Cancelado
     - SIM cancelado; fora de uso.
   * - ``IN``
     - Indisponível
     - SIM indisponível temporariamente (manutenção, bloqueio, etc.).
   * - ``TC``
     - Troca
     - SIM reservado para processo de troca.

Status dos Números de Voz
==========================

Status possíveis para ``VoiceNumbers.number_status``:

.. list-table:: Status de Número de Voz
   :header-rows: 1
   :widths: 10 20 70

   * - Código
     - Nome
     - Descrição
   * - ``DS``
     - Disponível
     - Número disponível para atribuição.
   * - ``AT``
     - Ativado
     - Número ativo em um plano de voz.
   * - ``CC``
     - Cancelado
     - Número cancelado.
   * - ``IN``
     - Indisponível
     - Número indisponível.
   * - ``TC``
     - Troca
     - Número reservado para troca.
