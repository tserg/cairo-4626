import asyncio
import os
from typing import Callable, Tuple

from utils import Signer, str_to_felt, to_uint

import pytest
from starkware.starknet.services.api.contract_definition import ContractDefinition
from starkware.starknet.compiler.compile import compile_starknet_files
from starkware.starknet.testing.starknet import Starknet, StarknetContract


def here() -> str:
    return os.path.abspath(os.path.dirname(__file__))


def contract_path(contract_name: str) -> str:
    return os.path.join(here(), "..", "contracts", "erc4626", contract_name)


def compile_contract(contract_name: str) -> ContractDefinition:
    contract_src = contract_path(contract_name)
    return compile_starknet_files(
        [contract_src],
        debug_info=True,
        disable_hint_validation=True,
        cairo_path=[
            os.path.join(here(), "..", "contracts", "lib"),
        ],
    )


def compile_mock_contract(contract_name: str) -> ContractDefinition:
    contract_src = os.path.join(here(), "mocks", contract_name)
    return compile_starknet_files(
        [contract_src], debug_info=True, cairo_path=[os.path.join(here(), "mocks")]
    )


@pytest.fixture(scope="session")
def event_loop():
    return asyncio.new_event_loop()


@pytest.fixture(scope="session")
async def starknet() -> Starknet:
    starknet = await Starknet.empty()
    return starknet


@pytest.fixture(scope="session")
def users(starknet) -> Callable[[str], Tuple[Signer, StarknetContract]]:
    account_contract = compile_mock_contract("openzeppelin/account/Account.cairo")
    cache = {}

    async def get_or_create_user(name):
        hit = cache.get(name)
        if hit:
            return hit

        signer = Signer(abs(hash(name)))
        account = await starknet.deploy(
            contract_def=account_contract, constructor_calldata=[signer.public_key]
        )

        user = (signer, account)
        cache[name] = user
        return user

    return get_or_create_user


@pytest.fixture(scope="session")
async def asset(starknet, users) -> StarknetContract:
    contract = compile_mock_contract("openzeppelin/token/erc20/ERC20_Mintable.cairo")
    _, asset_owner = await users("asset_owner")

    return await starknet.deploy(
        contract_def=contract,
        constructor_calldata=[
            str_to_felt("Winning"),  # name
            str_to_felt("WIN"),  # symbol
            18,  # decimals
            *to_uint(10 ** 18),  # initial supply
            asset_owner.contract_address,  # recipient
            asset_owner.contract_address,  # owner
        ],
    )


@pytest.fixture(scope="session")
async def erc4626(starknet, asset) -> StarknetContract:
    contract = compile_contract("ERC4626.cairo")

    return await starknet.deploy(
        contract_def=contract,
        constructor_calldata=[
            str_to_felt("Vault of Winning"),
            str_to_felt("vWIN"),
            asset.contract_address,
        ],
    )


@pytest.fixture(scope="session")
async def terc4626(starknet) -> StarknetContract:
    contract = compile_contract("test_ERC4626.cairo")
    return await starknet.deploy(contract_def=contract)
