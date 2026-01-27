## Version 0.0.1

### Metadata
- **Datetime**: 2026-01-27 15:55:13
- **Description**: naive retrieval with raw law data

### Metrics
- **Total Queries**: 34
- **MAP@3**: 0.9265
- **MRR@3**: 0.9265
- **avg_precision@3**: 0.3235
- **avg_recall@3**: 0.9706
- **Config**: top_k=3

### Failed Cases (Recall < 1.0)
- **[L1-WAGE-002]** 雇主應置備勞工工資清冊，該清冊應保存幾年？
  - Recall: 0.00

### Manual Analysis
- **Error analysis**: 
- **Possible resolution**: 
- **Has implemented possible resolution**: 
- **Has failures fixed**:
## Version 0.0.2

### Metadata
- **Datetime**: 2026-01-27 15:57:44
- **Description**: parent-child indexing - fine: chunking (1), (2) and ㄧ、．..二、... with permeable append

### Metrics
- **Total Queries**: 34
- **MAP@3**: 0.9069
- **MRR@3**: 0.9069
- **avg_precision@3**: 0.3235
- **avg_recall@3**: 0.9706
- **Config**: top_k=3

### Failed Cases (Recall < 1.0)
- **[L1-WAGE-005]** 雇主提供之工資計算明細（薪資單），必須包含哪些具體事項？
  - Recall: 0.00

### Manual Analysis
- **Error analysis**: 
- **Possible resolution**: 
- **Has implemented possible resolution**: 
- **Has failures fixed**:



## Version 0.0.3

### Metadata
- **Datetime**: 2026-01-27 15:58:50
- **Description**: parent-child indexicoarse: chunking with only (1), (2)

### Metrics
- **Total Queries**: 34
- **MAP@3**: 0.9706
- **MRR@3**: 0.9706
- **avg_precision@3**: 0.3333
- **avg_recall@3**: 1.0000
- **Config**: top_k=3

### Manual Analysis
- **Error analysis**: 
- **Possible resolution**: 
- **Has implemented possible resolution**: 
- **Has failures fixed**: 
