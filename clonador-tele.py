#!/data/data/com.termux/files/usr/bin/python3
# -*- coding: utf-8 -*-

import asyncio
import os
import sys
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, FloodWaitError
from telethon.tl.types import Channel

SESSION_FILE = "telegram_session"

def limpar_tela():
    os.system('clear')

async def get_credentials():
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
    except:
        pass
    
    api_id, api_hash = await get_credentials()
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
    for i, (nome, id, user) in enumerate(todas_entidades, 1):
        tipo = "📢 Canal" if i <= len(canais) or not mostrar_grupos else "📁 Grupo"
        print(f"  {i:2d}. {tipo}: {nome}")
        print(f"      ID: {id}")
    
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

async def listar_topicos_grupo(client, grupo_id):
    """Lista todos os tópicos de um grupo (busca completa)"""
    print(f"\n{'='*60}")
    print("TÓPICOS ENCONTRADOS (Buscando...)")
    print(f"{'='*60}")
    
    grupo = await client.get_input_entity(grupo_id)
    topicos = {}
    
    # Busca TODAS as mensagens para encontrar tópicos
    async for msg in client.iter_messages(grupo, reverse=True):
        if msg.reply_to is None and msg.reply_to_msg_id:
            # É uma mensagem de tópico
            if msg.id not in topicos:
                preview = msg.message[:60] if msg.message else "🖼️ Mídia"
                topicos[msg.id] = preview
    
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
        
        qtd_msgs = input("Quantidade (0=todas, Enter=0): ").strip()
        qtd_msgs = int(qtd_msgs) if qtd_msgs else 0
        
        grupo_origem = await client.get_input_entity(origem)
        grupo_destino = await client.get_input_entity(destino)
        
        print("\n" + "="*60)
        print("INICIANDO CLONAGEM COMPLETA...")
        print("="*60)
        print("🔄 Processando... NÃO FECHE O TERMINAL!\n")
        
        count = 0
        erros = 0
        
        # Busca TODAS as mensagens do tópico em ordem CORRETA
        async for msg in client.iter_messages(grupo_origem, reply_to=topico_id, reverse=True, limit=None if qtd_msgs == 0 else qtd_msgs):
            try:
                await client.send_message(grupo_destino, msg.message, file=msg.media)
                count += 1
                
                # Atualiza a cada 10 msgs
                if count % 10 == 0:
                    print(f"✅ {count} mensagens copiadas...", end='\r')
                
                # Pequeno delay para evitar flood
                await asyncio.sleep(0.1)
                
            except FloodWaitError as e:
                print(f"\n⚠️ Flood! Aguardando {e.seconds}s...")
                await asyncio.sleep(e.seconds)
            except Exception as e:
                erros += 1
                if erros < 5:  # Mostra apenas os 5 primeiros erros
                    print(f"\n⚠️ Erro (msg {count}): {e}")
        
        print(f"\n{'='*60}")
        print(f"🎉 CONCLUÍDO!")
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
        
        count = 0
        erros = 0
        
        # Busca TODAS as mensagens em ordem CORRETA
        async for msg in client.iter_messages(canal_origem, reverse=True, limit=None if qtd_msgs == 0 else qtd_msgs):
            try:
                await client.send_message(canal_destino, msg.message, file=msg.media)
                count += 1
                
                if count % 10 == 0:
                    print(f"✅ {count} mensagens copiadas...", end='\r')
                
                await asyncio.sleep(0.1)
                
            except FloodWaitError as e:
                print(f"\n⚠️ Flood! Aguardando {e.seconds}s...")
                await asyncio.sleep(e.seconds)
            except Exception as e:
                erros += 1
                if erros < 5:
                    print(f"\n⚠️ Erro (msg {count}): {e}")
        
        print(f"\n{'='*60}")
        print(f"🎉 CONCLUÍDO!")
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
        topicos = []
        
        # Encontra TODOS os tópicos
        async for msg in client.iter_messages(grupo_origem, reverse=True):
            if msg.reply_to is None and msg.reply_to_msg_id:
                if msg.id not in topicos:
                    topicos.append(msg.id)
        
        if not topicos:
            print("❌ Nenhum tópico encontrado!")
            return
        
        print(f"✅ Encontrados {len(topicos)} tópicos!\n")
        
        # Clona cada tópico
        for idx, topico_id in enumerate(topicos, 1):
            print(f"\n{'-'*50}")
            print(f"📌 Tópico {idx}/{len(topicos)} (ID: {topico_id})")
            print(f"{'-'*50}")
            
            count = 0
            erros = 0
            
            async for topico_msg in client.iter_messages(grupo_origem, reply_to=topico_id, reverse=True, limit=None if qtd == 0 else qtd):
                try:
                    await client.send_message(grupo_destino, topico_msg.message, file=topico_msg.media)
                    count += 1
                    print(f"  ✅ {count} msgs", end='\r')
                    await asyncio.sleep(0.1)
                except Exception as e:
                    erros += 1
            
            print(f"  📊 Concluído: {count} msgs copiadas")
        
        print("\n" + "="*60)
        print("🎉 TODOS OS TÓPICOS FORAM CLONADOS!")
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
