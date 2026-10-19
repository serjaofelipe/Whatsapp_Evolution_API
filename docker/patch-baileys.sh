#!/bin/sh
# Correção da Baileys aplicada toda vez que o container da Evolution API sobe.
#
# Avisos de grupo do tipo "participante trocou de número" às vezes chegam com
# parâmetros que não são JSON. A Baileys faz JSON.parse direto, dá erro ao
# processar as mensagens offline e a fila de eventos trava (o bot para de
# receber mensagens). Aqui trocamos por um parse que só ignora o item inválido.
#
# Se uma versão futura da imagem já tiver corrigido, o sed não encontra nada
# e o arquivo fica como está.
F=/evolution/node_modules/baileys/lib/Utils/process-message.js
if [ -f "$F" ] && grep -q 'messageStubParameters.map((a) => JSON.parse(a))' "$F"; then
    sed -i 's/messageStubParameters\.map((a) => JSON\.parse(a))/messageStubParameters.flatMap((a) => { try { return [JSON.parse(a)]; } catch { return []; } })/g' "$F"
    echo "[patch-baileys] Correção aplicada."
fi
