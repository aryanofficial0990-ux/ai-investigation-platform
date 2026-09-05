const express = require('express');
const grpc = require('@grpc/grpc-js');
const { connect, signers } = require('@hyperledger/fabric-gateway');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const app = express();
const PORT = 3001;

app.use(express.json());

// --- Fabric Connection Setup ---
const channelName = 'mychannel';
const chaincodeName = 'basic';
const mspId = 'Org1MSP';

// Corrected paths based on your environment
const cryptoPath = path.resolve(__dirname, '..', 'fabric-samples', 'test-network', 'organizations', 'peerOrganizations', 'org1.example.com');
const keyDirectoryPath = path.resolve(cryptoPath, 'users', 'User1@org1.example.com', 'msp', 'keystore');
const certPath = path.resolve(cryptoPath, 'users', 'User1@org1.example.com', 'msp', 'signcerts', 'User1@org1.example.com-cert.pem');
const tlsCertPath = path.resolve(cryptoPath, 'peers', 'peer0.org1.example.com', 'tls', 'ca.crt');
const peerEndpoint = 'localhost:7051';
const peerHostAlias = 'peer0.org1.example.com';

async function newGrpcConnection() {
    const tlsRootCert = fs.readFileSync(tlsCertPath);
    const tlsCredentials = grpc.credentials.createSsl(tlsRootCert);
    return new grpc.Client(peerEndpoint, tlsCredentials, {
        'grpc.ssl_target_name_override': peerHostAlias,
    });
}

function newIdentity() {
    const credentials = fs.readFileSync(certPath);
    return { mspId, credentials };
}

function newSigner() {
    const files = fs.readdirSync(keyDirectoryPath);
    const keyPath = path.resolve(keyDirectoryPath, files[0]);
    const privateKeyPem = fs.readFileSync(keyPath);
    const privateKey = crypto.createPrivateKey(privateKeyPem);
    return signers.newPrivateKeySigner(privateKey);
}

// --- API Endpoints ---

// 1. POST: Automatically hash evidence and log it to the blockchain
app.post('/api/evidence/log', async (req, res) => {
    try {
        const { id, investigatorID, timestamp, rawEvidence } = req.body;
        
        // Generate cryptographic SHA-256 hash of the evidence
        const fileHash = crypto.createHash('sha256').update(JSON.stringify(rawEvidence)).digest('hex');
        
        const client = await newGrpcConnection();
        const gateway = connect({
            client,
            identity: newIdentity(),
            signer: newSigner(),
            evaluateOptions: () => { return { deadline: Date.now() + 5000 }; },
            endorseOptions: () => { return { deadline: Date.now() + 15000 }; },
            submitOptions: () => { return { deadline: Date.now() + 5000 }; },
            commitStatusOptions: () => { return { deadline: Date.now() + 60000 }; },
        });

        const network = gateway.getNetwork(channelName);
        const contract = network.getContract(chaincodeName);

        console.log(`\n--> Submitting Transaction: RecordFinding for ID ${id} with Hash ${fileHash}`);
        
        await contract.submitTransaction(
            'RecordFinding', 
            String(id), 
            String(investigatorID), 
            String(fileHash), 
            String(timestamp)
        );
        
        gateway.close();
        client.close();

        return res.status(200).json({
            success: true,
            hashGenerated: fileHash,
            message: `Finding ${id} successfully committed to the blockchain.`
        });
    } catch (error) {
        console.error('--- BLOCKCHAIN REJECTION ---');
        console.error('Basic Error:', error.message);
        
        if (error.details && error.details.length > 0) {
            error.details.forEach(detail => {
                console.error('Chaincode Error:', detail.message);
            });
        }
        
        return res.status(500).json({ 
            error: "Failed to endorse transaction", 
            details: error.details ? error.details.map(d => d.message) : error.message 
        });
    }
});

// 2. GET: Retrieve evidence from the blockchain by ID
app.get('/api/evidence/:id', async (req, res) => {
    try {
        const findingID = req.params.id;
        
        const client = await newGrpcConnection();
        const gateway = connect({
            client,
            identity: newIdentity(),
            signer: newSigner(),
        });

        const network = gateway.getNetwork(channelName);
        const contract = network.getContract(chaincodeName);

        console.log(`\n--> Evaluating Transaction: GetFinding for ID ${findingID}`);

        const resultBytes = await contract.evaluateTransaction('GetFinding', String(findingID));
        const resultJSON = Buffer.from(resultBytes).toString('utf8');
        const finding = JSON.parse(resultJSON);

        gateway.close();
        client.close();

        return res.status(200).json(finding);
    } catch (error) {
        console.error('Error retrieving finding:', error.message);
        return res.status(500).json({ error: "Failed to retrieve evidence", details: error.message });
    }
});

app.listen(PORT, () => {
    console.log(`Blockchain API Gateway running on port ${PORT}`);
});