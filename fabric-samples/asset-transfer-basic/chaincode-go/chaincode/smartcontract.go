package chaincode

import (
	"encoding/json"
	"fmt"

	"github.com/hyperledger/fabric-contract-api-go/v2/contractapi"
)

// SmartContract provides functions for auditing investigation findings
type SmartContract struct {
	contractapi.Contract
}

// Finding represents an audit record on the blockchain
type Finding struct {
	InvestigatorID string `json:"investigatorID"`
	FileHash       string `json:"fileHash"`
	Timestamp      string `json:"timestamp"`
}

// RecordFinding anchors a new piece of evidence to the ledger
func (s *SmartContract) RecordFinding(ctx contractapi.TransactionContextInterface, findingID string, investigatorID string, fileHash string, timestamp string) error {
	exists, err := s.FindingExists(ctx, findingID)
	if err != nil {
		return err
	}
	if exists {
		return fmt.Errorf("the finding %s already exists", findingID)
	}

	finding := Finding{
		InvestigatorID: investigatorID,
		FileHash:       fileHash,
		Timestamp:      timestamp,
	}
	
	findingJSON, err := json.Marshal(finding)
	if err != nil {
		return err
	}

	return ctx.GetStub().PutState(findingID, findingJSON)
}

// GetFinding retrieves an audit record by its ID
func (s *SmartContract) GetFinding(ctx contractapi.TransactionContextInterface, findingID string) (*Finding, error) {
	findingJSON, err := ctx.GetStub().GetState(findingID)
	if err != nil {
		return nil, fmt.Errorf("failed to read from ledger: %v", err)
	}
	if findingJSON == nil {
		return nil, fmt.Errorf("the finding %s does not exist", findingID)
	}

	var finding Finding
	err = json.Unmarshal(findingJSON, &finding)
	if err != nil {
		return nil, err
	}

	return &finding, nil
}

// FindingExists checks if a finding is already on the ledger
func (s *SmartContract) FindingExists(ctx contractapi.TransactionContextInterface, findingID string) (bool, error) {
	findingJSON, err := ctx.GetStub().GetState(findingID)
	if err != nil {
		return false, fmt.Errorf("failed to read from ledger: %v", err)
	}
	return findingJSON != nil, nil
}