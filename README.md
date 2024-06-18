## zkSync Airdrop Claimer

## Config

Change options on the begining of claim.py file:
Put your own rpc on `rpc_url`

Gas price & gas limit configuration:
- You can put a fixed gas price on `gas_price`. Put it to 0 to use the next option:
- You can use a multiplier over current gas price on `gas_multiplier`. Some times fails if you use float numbers. Put it to 0 to use the next option.
- You can put a fixed eth cost on `max_eth_cost` and it will calculate the gasPrice for that ETH quantity. So you'll burn that ETH on fees!! Put it to 0 to use the next option.

***The easy way:*** put `gas_price`=0 and `gas_multiplier=1` so it will use the current gas price.

- `max_gas_price` is the maximun price of gas ever. It doesn't matter wich numbers you put before. The gas price will never be over this value.

- `gas_limit`: Fixed gas limit to use. Don't change it unless you know what are you doing.


## Installation

- Install python 3.10+
- Install requirements by command:
`pip install -r requirements.txt`
- Put your private keys on private_keys.txt
- Launch by command:
`python claim.py`
