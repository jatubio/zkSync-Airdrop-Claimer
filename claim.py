import requests
from fake_useragent import UserAgent
from loguru import logger

import json
import time
from web3 import Web3
from datetime import datetime

# RPC (PONER AQUí TU RPC)
rpc_url="https://zksync.drpc.org"

# Precio del gas. Si lo rellenas, tiene preferencia sobre el siguiente.
# Ponlo a 0 para usar el multiplicador
gas_price=0
# Multiplicador del gas poner a 0 para usar el gasto máximo
gas_multiplier=1
# Gasto máximo en ETH
max_eth_cost=0.001
# Máximo gas price que no se excederá nunca
max_gas_price=1

# Gas Límite usado en la transacción. Si se pone a 0, se estimará automáticamente.
gas_limit=0

# Año, Mes, Día, Hora, Minuto, Segundo (UTC)
target_time=int(datetime(2024,6,17,22,00,00).timestamp())

# Claim URL
claim_url = 'https://api.zknation.io/eligibility?id='

# Contratos
claim_contract_address = '0x66Fd4FC8FA52c9bec2AbA368047A0b27e24ecfe4'
token_contract_address = '0x5a7d6b2f92c77fad6ccabd7ee0624e64907eaf3e'

# Leer Abis
with open('claim_contract_abi.json', 'r') as abi_file:
    claim_contract_abi = json.load(abi_file)

with open('token_contract_abi.json', 'r') as abi_file:
    token_contract_abi = json.load(abi_file)

## Métodos comunes
def wait_until_target_time(target_time):

    print(datetime.fromtimestamp(target_time).strftime("Vamos a esperar hasta la hora %H:%M:%S del día %d del %m de %Y"))

    while True:
        current_time = int(time.time())
        time_left = target_time - current_time
        if time_left <= 0:
            break
        print(f"Esperando: {seconds_to_dhms(time_left)}")
        time.sleep(1)

def seconds_to_dhms(seconds):
    # Calcular días
    days = seconds // (24 * 3600)
    seconds %= (24 * 3600)

    # Calcular horas
    hours = seconds // 3600
    seconds %= 3600

    # Calcular minutos
    minutes = seconds // 60
    seconds %= 60

    # Los segundos restantes
    remaining_seconds = seconds

    # Formatear la cadena de salida
    result = f"{days} días, {hours} horas, {minutes} minutos y {remaining_seconds} segundos"

    return result

def load_data(file_path):
    with open(file_path, 'r') as file:
        return [line.strip() for line in file.readlines()]

def get_headers():
    ua = UserAgent()
    return {
        "Content-Type": 'application/json',
        "User-Agent": ua.random,
        "referer": 'https://claim.zknation.io/',
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Origin": "https://claim.zknation.io",
        "Sec-Ch-Ua": '"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
        "Sec-Ch-Ua-Mobile": "?1",
        "Sec-Ch-Ua-Platform": '"Android"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
        'x-api-key': '46001d8f026d4a5bb85b33530120cd38',
    }

## Métodos Web3
def connect_to_rpc():
    web3 = Web3(Web3.HTTPProvider(rpc_url))

        # Check if the connection is successful
    if not web3.is_connected():
        raise Exception("Failed to connect to zkSync RPC")
    else:
        print("Conectado al RPC!")

    return web3

def check_balance(account, web3):
    try:
        token_contract = web3.eth.contract(
            address=web3.to_checksum_address(token_contract_address),
            abi=token_contract_abi
        )
        balance = token_contract.functions.balanceOf(account.address).call()
        return balance

    except Exception as e:
        logger.error(f"Error checking balance for wallet {account.address}: {e}")
        return 0

## Métodos Airdrop zkSync
def process_wallet(key, web3):
    account = web3.eth.account.from_key(key)

    logger.info(f"Procesando la wallet {account.address}")

    # balance = check_balance(account, web3)
    # if balance > 0:
    #     logger.info(f"{account.address} | Tokens already claimed, balance: {int(balance / 10 ** 18)} $ZK")
    #     # transfer_tokens(account, key, balance, deposit_address, web3)
    #     return

    eligibility_data = get_eligibility(account.address)
    if not eligibility_data:
        logger.error(f"{account.address} | Failed to retrieve api data")
        return

    logger.success(f"{account.address} | Successfully retrieved data for claim")

    token_amount = claim_tokens(account, key, eligibility_data, web3)

    if token_amount is None:
        try:
            allocation = eligibility_data['allocations'][0]
            token_amount = int(allocation['tokenAmount'])
        except Exception as e:
            logger.error(f"{account.address} | Failed to retrieve token amount: {e}")
            return
    else:
        logger.success(f"{account.address} | Successfully claimed {int(token_amount / 10 ** 18)} $ZK")

def get_eligibility(wallet_address):
    url = f'{claim_url}{wallet_address}'

    headers = get_headers()

    try:
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"An error occurred: {e}")
        return None

def set_transaction_gas(transaction):
    if(gas_limit>0):
        estimated_gas = gas_limit
        logger.info(f"Usando un límite de gas FIJO: {gas_limit}")
    else:
        estimated_gas = web3.eth.estimate_gas(transaction)
        logger.info(f"Usando un límite de gas ESTIMADO: {estimated_gas}")

    # Calcular el gasPrice basado en las constantes de configuración
    if gas_price > 0:
        # Usar el gas_price proporcionado
        gas_price_wei = web3.to_wei(gas_price, 'gwei')
        logger.info(f"Usando un precio de gas FIJO: {gas_price}")
    elif gas_multiplier > 0:
        # Calcular el gasPrice usando el multiplicador respecto al gasPrice actual
        current_gas_price_wei = web3.eth.gas_price
        gas_price_wei = current_gas_price_wei * gas_multiplier
        logger.info(f"Usando un precio de gas {web3.from_wei(current_gas_price_wei, 'gwei')}x{gas_multiplier}: {web3.from_wei(gas_price_wei,'gwei')}")
    else:
        # Calcular el gasPrice a partir del máximo costo en ETH
        max_amount_wei = web3.to_wei(max_eth_cost, 'ether')
        gas_price_wei = max_amount_wei // estimated_gas
        logger.info(f"Usando un precio de gas {web3.from_wei(gas_price_wei, 'gwei')} para un gasto máximo de {max_eth_cost} ETH")

    # Asegurar que el gasPrice calculado no exceda del máximo permitido
    if gas_price_wei > web3.to_wei(max_gas_price, 'gwei'):
        gas_price_wei = web3.to_wei(max_gas_price, 'gwei')
        logger.info(f"El precio de gas se ha bajado al máximo: {web3.from_wei(gas_price_wei, 'gwei')}")

    # Actualizar la transacción con el gas estimado y el gasPrice calculado
    transaction['gas'] = estimated_gas
    transaction['gasPrice'] = gas_price_wei

    print(f'Gas estimado: {estimated_gas}')
    print(f'GasPrice calculado: {web3.from_wei(gas_price_wei, "gwei")} Gwei')

    return transaction

def claim_tokens(account, key, eligibility_data, web3):
    try:
        allocation = eligibility_data['allocations'][0]
        token_amount = int(allocation['tokenAmount'])
        merkle_proof = allocation['merkleProof']
        merkle_index = int(allocation['merkleIndex'])

        contract = web3.eth.contract(address=web3.to_checksum_address(claim_contract_address), abi=claim_contract_abi)

        transaction = contract.functions.claim(merkle_index, token_amount, merkle_proof).build_transaction({
            'gasPrice': web3.to_wei('1', 'gwei'),  # Un gasPrice inicial bajo para la estimación
            'from': account.address,
            'nonce': web3.eth.get_transaction_count(account.address),
        })

        transaction=set_transaction_gas(transaction)

        signed_txn = web3.eth.account.sign_transaction(transaction, private_key=key)
        claim_txn_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
        logger.success(f'{account.address} | Claim transaction sent: https://era.zksync.network/tx/{claim_txn_hash.hex()}')

        web3.eth.wait_for_transaction_receipt(claim_txn_hash)
        return token_amount
    except Exception as e:
        logger.error(f"{account.address} | Error claiming tokens: {e}")
        return None

## Módulo principal
if __name__ == "__main__":
    wait_until_target_time(target_time)

    web3=connect_to_rpc()
    wallets = load_data('private_keys.txt')

    for private_key in wallets:
        process_wallet(private_key, web3)
