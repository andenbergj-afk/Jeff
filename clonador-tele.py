#!/data/data/com.termux/files/usr/bin/python3
# -*- coding: utf-8 -*-

import asyncio
import os
import random
import sys
import time
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, FloodWaitError
from telethon.tl.functions.messages import GetForumTopicsRequest
from telethon.tl.types import Channel

SESSION_FILE = "telegram_session"

def limpar_tela():
    os.system('clear')

def get_credentials():
    if not os.path.exists(".env"):
        print("⚙️ PRIMEIRA CONFIGURAÇÃO!")
        print("Obtenha em: https://my.telegram.org\n")
        api_id = input("API ID (número): ").strip()
        api_hash = input("API HASH (código): ").strip()
        with open(".env", "w") as f:
            f.write(f"{api_id}\n{api_hash}\n")
        print("✅ Salvo!")
    
    with open(".env", "r") as f:
        linhas = f.readlines()
        return int(linhas[0].strip()), linhas[1].strip()

async def connect_client():
    try:
        if os.path.exists(f"{SESSION_FILE}.session-journal"):
            os.remove(f"{SESSION_FILE}.session-journal")
    except Exception:
        pass
    
    api_id, api_hash = get_credentials()
    client = TelegramClient(SESSION_FILE, api_id, api_hash)
    
    try:
        await client.connect()
        if not await client.is_user_authorized():
            print("\n🔐 Login necessário!")
            phone = input("Telefone (ex: +5511999999999): ")
            await client.send_code_request(phone)
            code = input("Código: ")
            
            try:
                await client.sign_in(phone, code)
            except SessionPasswordNeededError:
                print("\n🔑 Verificação de Duas Etapas ativada!")
                password = input("Digite sua senha (2FA): ")
                await client.sign_in(password=password)
                
        print("✅ Conectado!")
        return client
    except Exception as e:
        if "database is locked" in str(e):
            print("\n❌ Banco travado! Limpando...")
            os.remove(f"{SESSION_FILE}.session")
            print("✅ Execute NOVAMENTE.")
            sys.exit(0)
        print(f"❌ Erro: {e}")
        sys.exit(1)

# ============== FUNÇÃO DE SELEÇÃO ATUALIZADA ==============

async def listar_entidades(client, mostrar_canais=True, mostrar_grupos=True):
    """Lista canais e/ou grupos com tópicos"""
    canais = []
    grupos_topicos = []
    
    print("\n📲 Buscando suas conversas... aguarde...")
    
    async for dialog in client.iter_dialogs():
        entity = dialog.entity
        if isinstance(entity, Channel):
            if entity.megagroup and getattr(entity, 'forum', False) and mostrar_grupos:
                grupos_topicos.append((dialog.name, entity.id, entity.username))
            elif not entity.megagroup and mostrar_canais:
                canais.append((dialog.name, entity.id, entity.username))
    
    return canais, grupos_topicos

async def selecionar_entidade(client, tipo="origem", mostrar_canais=True, mostrar_grupos=True):
    """Permite selecionar canal/grupo da lista com paginação"""
    canais, grupos = await listar_entidades(client, mostrar_canais, mostrar_grupos)
    todas_entidades = canais + grupos
    
    if not todas_entidades:
        print("\n❌ Nenhuma conversa encontrada!")
        return int(input("Digite o ID manualmente: "))
    
    print(f"\n{'='*60}")
    print(f"SELECIONAR LOCAL DE {tipo.upper()}")
    print(f"{'='*60}")
    
    # Mostra lista numerada
    for i, (nome, eid, _) in enumerate(todas_entidades, 1):
        tipo_label = "📢 Canal" if i <= len(canais) else "📁 Grupo"
        print(f"  {i:2d}. {tipo_label}: {nome}")
        print(f"      ID: {eid}")
    
    print(f"\n  {len(todas_entidades) + 1}. 📝 Digitar ID manualmente")
    
    while True:
        try:
            escolha = int(input(f"\nEscolha (1-{len(todas_entidades) + 1}): "))
            if 1 <= escolha <= len(todas_entidades):
                return todas_entidades[escolha - 1][1]
            elif escolha == len(todas_entidades) + 1:
                return int(input("Digite o ID: "))
            else:
                print("❌ Número inválido!")
        except ValueError:
            print("❌ Digite apenas números!")

async def _obter_topicos_forum(client, grupo):
    """Obtém tópicos do fórum via API oficial (rápido, sem iterar mensagens)."""
    topicos = {}
    offset_topic = 0
    while True:
        result = await client(GetForumTopicsRequest(
            channel=grupo,
            q='',
            offset_date=0,
            offset_id=0,
            offset_topic=offset_topic,
            limit=100,
        ))
        if not result.topics:
            break
        for topic in result.topics:
            topicos[topic.id] = topic.title
        if len(result.topics) < 100:
            break
        offset_topic = result.topics[-1].id
    return topicos

async def listar_topicos_grupo(client, grupo_id):
    """Lista todos os tópicos de um grupo usando a API oficial."""
    print(f"\n{'='*60}")
    print("TÓPICOS ENCONTRADOS (Buscando...)")
    print(f"{'='*60}")
    
    grupo = await client.get_input_entity(grupo_id)
    topicos = await _obter_topicos_forum(client, grupo)
    
    if not topicos:
        print("❌ Nenhum tópico encontrado!")
        return None
    
    print(f"\n✅ Encontrados {len(topicos)} tópicos!\n")
    
    # Mostra tópicos numerados
    topicos_list = list(topicos.items())[:20]  # Mostra até 20
    
    for i, (t_id, titulo) in enumerate(topicos_list, 1):
        print(f"  {i:2d}. ID: {t_id:>10} | {titulo}...")
    
    if len(topicos) > 20:
        print(f"\n  ... e mais {len(topicos) - 20} tópicos")
    
    print(f"\n  {len(topicos_list) + 1}. 📝 Digitar ID do tópico manualmente")
    
    while True:
        try:
            escolha = int(input(f"\nEscolha tópico (1-{len(topicos_list) + 1}): "))
            if 1 <= escolha <= len(topicos_list):
                return topicos_list[escolha - 1][0]
            elif escolha == len(topicos_list) + 1:
                return int(input("Digite o ID do tópico: "))
            else:
                print("❌ Número inválido!")
        except ValueError:
            print("❌ Digite apenas números!")

# ============== FUNÇÕES DE CLONAGEM Otimizadas ==============

async def _clonar_mensagens(client, origem, destino, reply_to=None, limit=None, indent=""):
    """Encaminha mensagens em lotes para destino com controle de flood."""
    count = 0
    erros = 0
    BATCH_SIZE = 50         # lotes menores reduzem a chance de flood
    SLEEP_ENTRE_LOTES = 2   # segundos entre cada lote de mensagens
    SLEEP_APOS_FLOOD = 5    # segundos extras após recuperar de FloodWait
    MAX_TENTATIVAS = 10     # máximo de retentativas por lote

    kwargs = {"reverse": True, "limit": limit}
    if reply_to is not None:
        kwargs["reply_to"] = reply_to

    batch = []

    async def _enviar_lote(ids):
        nonlocal count, erros
        for tentativa in range(1, MAX_TENTATIVAS + 1):
            try:
                await client.forward_messages(destino, ids, origem, drop_author=True)
                count += len(ids)
                print(f"{indent}✅ {count} mensagens copiadas...", end='\r')
                return
            except FloodWaitError as e:
                wait = e.seconds + SLEEP_APOS_FLOOD
                print(
                    f"\n{indent}⚠️ Flood! Aguardando {wait}s... "
                    f"(tentativa {tentativa}/{MAX_TENTATIVAS})"
                )
                await asyncio.sleep(wait)
            except Exception as e:
                erros += len(ids)
                print(f"\n{indent}⚠️ Erro no lote: {e}")
                return
        erros += len(ids)
        print(f"\n{indent}⚠️ Lote ignorado após {MAX_TENTATIVAS} tentativas de FloodWait.")

    async for msg in client.iter_messages(origem, **kwargs):
        batch.append(msg.id)
        if len(batch) >= BATCH_SIZE:
            await _enviar_lote(batch)
            batch = []
            await asyncio.sleep(SLEEP_ENTRE_LOTES)

    if batch:
        await _enviar_lote(batch)

    return count, erros

async def clonar_topico_especifico(client):
    print("\n" + "="*60)
    print("COPIAR TÓPICO ESPECÍFICO")
    print("="*60)
    
    try:
        # SELEÇÃO AUTOMÁTICA
        if input("\n🎯 Usar seleção automática? (s/n): ").lower().startswith('s'):
            origem = await selecionar_entidade(client, "ORIGEM", mostrar_canais=False, mostrar_grupos=True)
            topico_id = await listar_topicos_grupo(client, origem)
            destino = await selecionar_entidade(client, "DESTINO")
        else:
            origem = int(input("ID grupo origem: "))
            topico_id = int(input("ID tópico: "))
            destino = int(input("ID grupo destino: "))
        
        if topico_id is None:
            print("❌ Nenhum tópico selecionado.")
            return
        
        qtd_msgs = input("Quantidade (0=todas, Enter=0): ").strip()
        qtd_msgs = int(qtd_msgs) if qtd_msgs else 0
        
        grupo_origem = await client.get_input_entity(origem)
        grupo_destino = await client.get_input_entity(destino)
        
        print("\n" + "="*60)
        print("INICIANDO CLONAGEM COMPLETA...")
        print("="*60)
        print("🔄 Processando... NÃO FECHE O TERMINAL!\n")
        
        inicio = time.monotonic()
        count, erros = await _clonar_mensagens(
            client, grupo_origem, grupo_destino,
            reply_to=topico_id,
            limit=None if qtd_msgs == 0 else qtd_msgs,
        )
        elapsed = time.monotonic() - inicio
        
        print(f"\n{'='*60}")
        print(f"🎉 CONCLUÍDO! ({elapsed:.0f}s)")
        print(f"✅ Total: {count} mensagens copiadas")
        print(f"❌ Erros: {erros}")
        print(f"{'='*60}")
        
    except KeyboardInterrupt:
        print("\n\n🛑 CLONAGEM INTERROMPIDA PELO USUÁRIO!")
    except Exception as e:
        print(f"\n❌ Erro crítico: {e}")

async def clonar_canal(client):
    print("\n" + "="*60)
    print("CLONAR CANAL COMPLETO")
    print("="*60)
    
    try:
        # SELEÇÃO AUTOMÁTICA
        if input("\n🎯 Usar seleção automática? (s/n): ").lower().startswith('s'):
            origem = await selecionar_entidade(client, "ORIGEM (de onde COPIAR)", mostrar_canais=True, mostrar_grupos=False)
            destino = await selecionar_entidade(client, "DESTINO (onde COLAR)", mostrar_canais=True, mostrar_grupos=False)
        else:
            origem = input("ID/@ canal origem: ")
            destino = input("ID/@ canal destino: ")
        
        qtd_msgs = input("Quantidade (0=todas, Enter=0): ").strip()
        qtd_msgs = int(qtd_msgs) if qtd_msgs else 0
        
        canal_origem = await client.get_input_entity(origem)
        canal_destino = await client.get_input_entity(destino)
        
        print("\n" + "="*60)
        print("INICIANDO CLONAGEM COMPLETA...")
        print("="*60)
        print("🔄 Processando... NÃO FECHE O TERMUX!\n")
        
        inicio = time.monotonic()
        count, erros = await _clonar_mensagens(
            client, canal_origem, canal_destino,
            limit=None if qtd_msgs == 0 else qtd_msgs,
        )
        elapsed = time.monotonic() - inicio
        
        print(f"\n{'='*60}")
        print(f"🎉 CONCLUÍDO! ({elapsed:.0f}s)")
        print(f"✅ Total: {count} mensagens copiadas")
        print(f"❌ Erros: {erros}")
        print(f"{'='*60}")
        
    except KeyboardInterrupt:
        print("\n\n🛑 CLONAGEM INTERROMPIDA PELO USUÁRIO!")
    except Exception as e:
        print(f"\n❌ Erro crítico: {e}")

async def clonar_todos_topicos(client):
    print("\n" + "="*60)
    print("CLONAR TODOS OS TÓPICOS")
    print("="*60)
    
    try:
        if input("\n🎯 Usar seleção automática? (s/n): ").lower().startswith('s'):
            origem = await selecionar_entidade(client, "ORIGEM", mostrar_canais=False, mostrar_grupos=True)
            destino = await selecionar_entidade(client, "DESTINO")
        else:
            origem = int(input("ID grupo origem: "))
            destino = int(input("ID grupo destino: "))
        
        qtd = input("Mensagens por tópico (0=todas, Enter=0): ").strip()
        qtd = int(qtd) if qtd else 0
        
        grupo_origem = await client.get_input_entity(origem)
        grupo_destino = await client.get_input_entity(destino)
        
        print("\n📲 Buscando tópicos...")
        topicos = await _obter_topicos_forum(client, grupo_origem)
        topicos_ids = list(topicos.keys())
        if not topicos_ids:
            print("❌ Nenhum tópico encontrado!")
            return
        
        print(f"✅ Encontrados {len(topicos_ids)} tópicos!\n")
        
        total_count = 0
        total_erros = 0
        inicio_total = time.monotonic()
        
        # Clona cada tópico
        for idx, topico_id in enumerate(topicos_ids, 1):
            print(f"\n{'-'*50}")
            print(f"📌 Tópico {idx}/{len(topicos_ids)} (ID: {topico_id})")
            print(f"{'-'*50}")
            
            count, erros = await _clonar_mensagens(
                client, grupo_origem, grupo_destino,
                reply_to=topico_id,
                limit=None if qtd == 0 else qtd,
                indent="  ",
            )
            total_count += count
            total_erros += erros
            print(f"  📊 Concluído: {count} msgs copiadas, {erros} erros")
            if idx < len(topicos_ids):
                print(f"  ⏳ Aguardando 3s antes do próximo tópico...")
                await asyncio.sleep(3)
        
        elapsed = time.monotonic() - inicio_total
        print("\n" + "="*60)
        print(f"🎉 TODOS OS TÓPICOS FORAM CLONADOS! ({elapsed:.0f}s)")
        print(f"✅ Total: {total_count} mensagens | ❌ Erros: {total_erros}")
        print("="*60)
        
    except KeyboardInterrupt:
        print("\n\n🛑 CLONAGEM INTERROMPIDA PELO USUÁRIO!")
    except Exception as e:
        print(f"\n❌ Erro: {e}")

async def menu_principal():
    MENU = """
╔════════════════════════════════════════════════════════════╗
║        CLONADOR KHAOSTHEVOID | TOTALMENTE SEM LIMITES      ║
╠════════════════════════════════════════════════════════════╣
║ 1. Clonar UM tópico de grupo (com lista de tópicos)        ║
║ 2. Clonar TODOS os tópicos de grupo                        ║
║ 3. Clonar canal completo (TODAS as mensagens)              ║
║ 4. Sair                                                    ║
╚════════════════════════════════════════════════════════════╝
"""
    client = await connect_client()
    
    try:
        while True:
            limpar_tela()
            print(MENU)
            
            opcao = input("\nOpção (1-4): ").strip()
            
            if opcao == "1":
                await clonar_topico_especifico(client)
            elif opcao == "2":
                await clonar_todos_topicos(client)
            elif opcao == "3":
                await clonar_canal(client)
            elif opcao == "4":
                print("👋 Saindo...")
                break
            else:
                print("⚠️ Opção inválida!")
            
            input("\nENTER para continuar...")
    
    finally:
        await client.disconnect()

if __name__ == "__main__":
    try:
        from telethon import TelegramClient
    except ImportError:
        print("❌ Telethon não encontrado!")
        print("💡 Execute: pip install telethon")
        sys.exit(1)
    
    limpar_tela()
    print("🚀 INICIANDO CLONADOR ILIMITADO...")
    asyncio.run(menu_principal())
