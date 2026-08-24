# Real On-Chain Sends (Wallet+)

## Current Status
- **Simulation mode** (default): Send only updates your internal database balance. No crypto moves on any blockchain.
- **Real mode**: When you have a **real external wallet connected** (MetaMask, Trust Wallet, Phantom, etc.) via "Connect to Wallet", sending ETH will trigger a **real transaction** from your connected wallet.

Crypto will **actually arrive** at the destination address on the blockchain.

## How to Send Real Crypto
1. Click **"Connect to Wallet"** (bottom of dashboard).
2. Use a real installed wallet:
   - Desktop: MetaMask / Trust Wallet extension (unlock it first).
   - Phone: Open Trust/MetaMask/Phantom app → Browser tab → load this site → Connect.
3. Make sure your wallet is on the correct network (Sepolia testnet recommended for first tries).
4. Open **Send Crypto**.
5. Select **ethereum (ETH)**.
6. Enter amount (in ETH) and destination address.
7. Click Send.
8. Your wallet will pop up to confirm the transaction + gas.
9. Once confirmed on-chain, the crypto **really arrives**.

You will see a transaction hash and Etherscan link.

## Important Warnings
- **Gas fees**: You pay real network fees from the connected wallet.
- **Testnet first**: Use Sepolia. Get free test ETH from faucets:
  - https://sepoliafaucet.com
  - https://www.alchemy.com/faucets/ethereum-sepolia
- **Mainnet**: Only use if you understand you are sending real money.
- **Only ETH native** is supported for real sends right now (ERC20 tokens, BTC, SOL etc. still simulated).
- Never send to wrong networks or addresses.
- The app never sees your private keys — signing happens in your wallet.

## Server Hot Wallet (Advanced / Future)
For sending from your *internal app balance* as real on-chain crypto, a server-side hot wallet with private key + funded RPC is required.
This is **not enabled by default** because it is custodial and risky.
See `.env.example` for the variables if you want to experiment (ETH only).

## Adding Real Balance Visibility (Future)
Currently external wallet balances show as 0 in the UI even after connecting.
Real on-chain balance queries require RPC keys (Alchemy, etc.). Can be added later.

## Security
- Always verify the destination address in your wallet popup.
- Double-check the network in your wallet.
- Start with tiny test amounts on Sepolia.

If you want full custodial real sends (app holds the keys and sends from "your app balance"), fund a hot wallet and configure the env vars, then we can enable the server path.
