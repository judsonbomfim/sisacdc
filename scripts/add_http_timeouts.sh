#!/bin/bash
# Script para adicionar timeout em todas as conexões HTTP sem timeout

echo "🔧 Adicionando timeout em conexões HTTP..."

# Backup dos arquivos
cp apps/sims/tasks.py apps/sims/tasks.py.bak
cp apps/sims/classes.py apps/sims/classes.py.bak
cp apps/voice_calls/tasks.py apps/voice_calls/tasks.py.bak

# Substituir HTTPSConnection( por HTTPSConnection(settings.X, timeout=10)
# Mas apenas onde NÃO há timeout já

# apps/sims/tasks.py - Linhas 218, 389, 583, 741
sed -i '218s/HTTPSConnection(settings.APITC_HTTPCONN)/HTTPSConnection(settings.APITC_HTTPCONN, timeout=10)/' apps/sims/tasks.py
sed -i '389s/HTTPSConnection(settings.APITC_HTTPCONN)/HTTPSConnection(settings.APITC_HTTPCONN, timeout=10)/' apps/sims/tasks.py
sed -i '583s/HTTPSConnection(settings.APITC_HTTPCONN)/HTTPSConnection(settings.APITC_HTTPCONN, timeout=10)/' apps/sims/tasks.py
sed -i '741s/HTTPSConnection(parsed_url.netloc)/HTTPSConnection(parsed_url.netloc, timeout=10)/' apps/sims/tasks.py

# apps/sims/classes.py - Linhas 215, 236, 275, 304, 415, 436
sed -i '215s/HTTPSConnection(settings.APITC_HTTPCONN)/HTTPSConnection(settings.APITC_HTTPCONN, timeout=10)/' apps/sims/classes.py
sed -i '236s/HTTPSConnection(settings.APITC_HTTPCONN)/HTTPSConnection(settings.APITC_HTTPCONN, timeout=10)/' apps/sims/classes.py
sed -i '275s/HTTPSConnection(settings.APITC_HTTPCONN)/HTTPSConnection(settings.APITC_HTTPCONN, timeout=10)/' apps/sims/classes.py
sed -i '304s/HTTPSConnection(settings.APITC_HTTPCONN)/HTTPSConnection(settings.APITC_HTTPCONN, timeout=10)/' apps/sims/classes.py
sed -i '415s/HTTPSConnection(settings.APITC_HTTPCONN)/HTTPSConnection(settings.APITC_HTTPCONN, timeout=10)/' apps/sims/classes.py
sed -i '436s/HTTPSConnection(settings.APITC_HTTPCONN)/HTTPSConnection(settings.APITC_HTTPCONN, timeout=10)/' apps/sims/classes.py

# apps/voice_calls/tasks.py - Linhas 183, 280
sed -i '183s/HTTPSConnection(parsed_url.netloc)/HTTPSConnection(parsed_url.netloc, timeout=10)/' apps/voice_calls/tasks.py
sed -i '280s/HTTPSConnection(parsed_url.netloc)/HTTPSConnection(parsed_url.netloc, timeout=10)/' apps/voice_calls/tasks.py

echo "✅ Timeout adicionado em 14 conexões HTTP"
echo "📝 Backups salvos em: *.bak"
echo ""
echo "Para verificar as mudanças:"
echo "  diff apps/sims/tasks.py apps/sims/tasks.py.bak"
echo "  diff apps/sims/classes.py apps/sims/classes.py.bak"
echo "  diff apps/voice_calls/tasks.py apps/voice_calls/tasks.py.bak"
