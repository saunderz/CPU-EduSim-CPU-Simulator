#include "cpu_backend.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// -----------------------------------------------------------
// Definições e limites
// -----------------------------------------------------------
#define MAX_MEM_SIZE   10         // 10 posições de memória
#define CACHE_LINES    4          // 4 linhas de cache
#define MAX_INSTR      100        // Máximo de instruções
#define MAX_STR_SIZE   512        // Tamanho máximo de cada instrução

// -----------------------------------------------------------
// Variáveis globais (originais)
// -----------------------------------------------------------
static int memoryData[MAX_MEM_SIZE];   // Memória principal
static int regR1, regR2, regR3, regR4; // Registradores

// Buffer estático para guardar as instruções (cada linha tem até MAX_STR_SIZE)
static char instructionBuffer[MAX_INSTR][MAX_STR_SIZE];

// Array de ponteiros para cada instrução
static char* instructionSet[MAX_INSTR];

static int   instructionCount   = 0;
static int   currentInstrIndex  = 0;

static char lastOperationText[MAX_STR_SIZE]   = "";
static char lastExplanationText[MAX_STR_SIZE] = "";

// Histórico
static char historyBuffer[4096] = "";

// Modo Explicação
static int explanationMode = 0;

// Ciclos
static int totalCycles    = 0;
static int lastInstrCost  = 0;

// -----------------------------------------------------------
// Estrutura da Cache
// -----------------------------------------------------------
typedef struct {
    int valid;   
    int tag;     
    int data;    
    int lastUse; 
} CacheLine;

static CacheLine cacheLines[CACHE_LINES];
static int cacheHits   = 0;
static int cacheMisses = 0;
static int globalUseCounter = 0;

// 0 = Mapeamento Direto (original), 1 = Associativo
static int mappingMode = 0;


// -----------------------------------------------------------
// Funções internas para a cache
// -----------------------------------------------------------
static void invalidateCache() {
    for(int i = 0; i < CACHE_LINES; i++){
        cacheLines[i].valid   = 0;
        cacheLines[i].tag     = -1;
        cacheLines[i].data    = 0;
        cacheLines[i].lastUse = 0;
    }
    cacheHits     = 0;
    cacheMisses   = 0;
    globalUseCounter = 0;
}

static void touchLine(CacheLine* line) {
    globalUseCounter++;
    line->lastUse = globalUseCounter;
}

static int getDirectMappingIndex(int addr) {
    return (addr % CACHE_LINES);
}

static int getAssociativeLineIndex(int addr, int* isHit) {
    *isHit = 0;
    int indexToReplace = -1;
    int oldestUse      = 999999999;

    for (int i = 0; i < CACHE_LINES; i++) {
        if (cacheLines[i].valid && cacheLines[i].tag == addr) {
            *isHit = 1;
            return i;
        }
    }
    // Não achou -> MISS
    for (int i = 0; i < CACHE_LINES; i++) {
        if (!cacheLines[i].valid) {
            return i; // linha livre
        }
        if (cacheLines[i].lastUse < oldestUse) {
            oldestUse = cacheLines[i].lastUse;
            indexToReplace = i;
        }
    }
    return indexToReplace;
}

static int accessCache(int address, int* outIndex) {
    int isHit = 0;
    int idx   = 0;

    if (mappingMode == 0) {
        // Mapeamento Direto
        idx = getDirectMappingIndex(address);
        if (cacheLines[idx].valid && cacheLines[idx].tag == address) {
            isHit = 1;
        } else {
            // MISS => carrega da memória
            cacheLines[idx].valid = 1;
            cacheLines[idx].tag   = address;
            cacheLines[idx].data  = memoryData[address];
        }
        touchLine(&cacheLines[idx]);
    }
    else {
        // Associativo
        idx = getAssociativeLineIndex(address, &isHit);
        if (!isHit) {
            // MISS => carrega da memória
            cacheLines[idx].valid = 1;
            cacheLines[idx].tag   = address;
            cacheLines[idx].data  = memoryData[address];
        }
        touchLine(&cacheLines[idx]);
    }

    if (isHit) cacheHits++; else cacheMisses++;
    if (outIndex) {
        *outIndex = idx;
    }
    return isHit;
}

// -----------------------------------------------------------
// LOAD/STORE (usado internamente)
// -----------------------------------------------------------
static int cacheLoad(int address, char* opTxt, char* expTxt) {
    if (address < 0 || address >= MAX_MEM_SIZE) {
        if (opTxt)  snprintf(opTxt,  MAX_STR_SIZE, "LOAD (addr=%d inválido)", address);
        if (expTxt) snprintf(expTxt, MAX_STR_SIZE, "Endereço fora da memória!");
        return -999;
    }
    int idx;
    int hit = accessCache(address, &idx);

    if (opTxt) {
        snprintf(opTxt, MAX_STR_SIZE, "LOAD: Memória[%d]", address);
    }
    if (expTxt) {
        if (hit) {
            snprintf(expTxt, MAX_STR_SIZE, "LOAD via Cache (HIT). Valor=%d", cacheLines[idx].data);
        } else {
            snprintf(expTxt, MAX_STR_SIZE, "LOAD via Memória (MISS). Valor=%d", cacheLines[idx].data);
        }
    }
    return cacheLines[idx].data;
}

static void cacheStore(int address, int value, char* opTxt, char* expTxt) {
    if (address < 0 || address >= MAX_MEM_SIZE) {
        if (opTxt)  snprintf(opTxt, MAX_STR_SIZE, "STORE (addr=%d inválido)", address);
        if (expTxt) snprintf(expTxt,MAX_STR_SIZE, "Endereço fora da memória!");
        return;
    }
    int idx;
    int hit = accessCache(address, &idx);

    cacheLines[idx].data = value;
    memoryData[address]  = value;

    if (opTxt) {
        snprintf(opTxt, MAX_STR_SIZE, "STORE: Memória[%d]", address);
    }
    if (expTxt) {
        if (hit) {
            snprintf(expTxt, MAX_STR_SIZE, "STORE com HIT. Valor %d escrito na cache e memória.", value);
        } else {
            snprintf(expTxt, MAX_STR_SIZE, "STORE com MISS. Valor %d escrito na cache e memória.", value);
        }
    }
}

// -----------------------------------------------------------
// Implementações exportadas
// -----------------------------------------------------------
DLL_EXPORT void initCPU(void) {
    // Inicializa a memória principal:
    // mem[0] = 0, mem[1] = 10, mem[2] = 20, ..., mem[9] = 90
    for (int i=0; i<MAX_MEM_SIZE; i++){
        memoryData[i] = i * 10;
    }
    // Zera registradores
    regR1 = regR2 = regR3 = regR4 = 0;

    // Invalida cache
    invalidateCache();

    // Zera histórico
    strcpy(historyBuffer, "");
    // Zera instruções (count e índice)
    instructionCount   = 0;
    currentInstrIndex  = 0;

    // Zera textos
    strcpy(lastOperationText, "");
    strcpy(lastExplanationText, "");

    totalCycles   = 0;
    lastInstrCost = 0;
    explanationMode = 0;

    // Mapeamento Direto por padrão
    mappingMode = 0;
}

DLL_EXPORT void resetCPU(void) {
    // Mantém instruções, mas reinicia memória, regs, cache, ciclos, histórico
    for (int i=0; i<MAX_MEM_SIZE; i++){
        memoryData[i] = i * 10;  // Reaplica i*10
    }
    regR1 = regR2 = regR3 = regR4 = 0;

    invalidateCache();

    strcpy(historyBuffer, "");
    currentInstrIndex = 0;

    totalCycles   = 0;
    lastInstrCost = 0;

    strcpy(lastOperationText, "");
    strcpy(lastExplanationText, "");
}

// Carrega instruções-padrão
DLL_EXPORT void loadDefaultInstructions(void) {
    // NOVA LISTA de 7 instruções
    static const char* defaultInstructs[] = {
        "LOAD R1, 5",
        "LOAD R2, 9",
        "ADD R3, R1, R2",
        "STORE R3, 2",
        "LOAD R4, 4",
        "SUB R1, R4, R2",
        "STORE R1, 3"
    };
    const int defaultCount = 7;

    for (int i=0; i<defaultCount; i++) {
        strncpy(instructionBuffer[i], defaultInstructs[i], MAX_STR_SIZE-1);
        instructionBuffer[i][MAX_STR_SIZE-1] = '\0';
        instructionSet[i] = instructionBuffer[i];
    }
    instructionCount   = defaultCount;
    currentInstrIndex  = 0;
}

DLL_EXPORT void setInstructions(char* instructions[], int count) {
    if (count > MAX_INSTR) {
        count = MAX_INSTR;
    }
    // Copia cada instrução do array passado para nosso buffer local
    for (int i=0; i<count; i++){
        if (instructions[i]) {
            strncpy(instructionBuffer[i], instructions[i], MAX_STR_SIZE-1);
            instructionBuffer[i][MAX_STR_SIZE-1] = '\0';
            instructionSet[i] = instructionBuffer[i];
        } else {
            // Se for nulo, considera string vazia
            instructionBuffer[i][0] = '\0';
            instructionSet[i] = instructionBuffer[i];
        }
    }
    instructionCount  = count;
    currentInstrIndex = 0;
}

DLL_EXPORT int getInstructionCount(void) {
    return instructionCount;
}

DLL_EXPORT const char* getInstructionLine(int index) {
    if (index < 0 || index >= instructionCount) {
        return "";
    }
    return instructionSet[index];
}

// -----------------------------------------------------------
// nextInstruction - Parsing robusto
// -----------------------------------------------------------
DLL_EXPORT void nextInstruction(void) {
    if (currentInstrIndex >= instructionCount) {
        strcpy(lastOperationText, "Fim das instruções");
        strcpy(lastExplanationText, "Não há mais instruções para executar.");
        lastInstrCost = 0;
        return;
    }
    const char* instr = instructionSet[currentInstrIndex];
    currentInstrIndex++;

    // Limpa textos
    strcpy(lastOperationText,   "");
    strcpy(lastExplanationText, "");

    // Parsing passo a passo
    char line[MAX_STR_SIZE];
    strncpy(line, instr, MAX_STR_SIZE-1);
    line[MAX_STR_SIZE - 1] = '\0';

    char op[16];
    op[0] = '\0';

    char* token = strtok(line, " \t");
    if (!token) {
        strcpy(lastOperationText, instr);
        strcpy(lastExplanationText, "Instrução inválida ou não reconhecida.");
        lastInstrCost = 0;
        return;
    }
    strncpy(op, token, sizeof(op)-1);
    op[sizeof(op)-1] = '\0';

    // Pega resto da linha
    char* rest = strtok(NULL, "\n");
    if (!rest) rest = "";

    // 1) LOAD / STORE
    if (strcmp(op, "LOAD") == 0 || strcmp(op, "STORE") == 0) {
        char regStr[8] = "";
        int  address    = 0;

        int ok = sscanf(rest, " %[^, \t], %d", regStr, &address);
        if (ok < 2) {
            // tenta sem vírgula
            ok = sscanf(rest, " %[^, \t] %d", regStr, &address);
        }
        if (ok < 2) {
            strcpy(lastOperationText, instr);
            strcpy(lastExplanationText, "Instrução LOAD/STORE inválida.");
            lastInstrCost = 0;
            return;
        }

        int regNum = 0;
        if (regStr[0] == 'R') {
            regNum = regStr[1] - '0';
        }

        if (strcmp(op, "LOAD") == 0) {
            int val = cacheLoad(address, lastOperationText, lastExplanationText);
            switch(regNum){
                case 1: regR1 = val; break;
                case 2: regR2 = val; break;
                case 3: regR3 = val; break;
                case 4: regR4 = val; break;
                default: break;
            }
            if (strstr(lastExplanationText, "HIT")) {
                lastInstrCost = 5;
            } else {
                lastInstrCost = 10;
            }
            totalCycles += lastInstrCost;

            char temp[64];
            snprintf(temp, sizeof(temp), "%s -> %s", lastOperationText, regStr);
            strcpy(lastOperationText, temp);
        }
        else {
            // STORE
            int val = 0;
            switch(regNum){
                case 1: val = regR1; break;
                case 2: val = regR2; break;
                case 3: val = regR3; break;
                case 4: val = regR4; break;
                default: val = 0;    break;
            }
            cacheStore(address, val, lastOperationText, lastExplanationText);

            if (strstr(lastExplanationText, "HIT")) {
                lastInstrCost = 5;
            } else {
                lastInstrCost = 10;
            }
            totalCycles += lastInstrCost;

            char temp[64];
            snprintf(temp, sizeof(temp), "%s (valor=%d) <- %s", lastOperationText, val, regStr);
            strcpy(lastOperationText, temp);
        }

    // 2) ADD / SUB
    } else if (strcmp(op, "ADD") == 0 || strcmp(op, "SUB") == 0) {
        char rDest[8] = "", rSrc1[8] = "", rSrc2[8] = "";
        int ok = sscanf(rest, " %[^,], %[^,], %s", rDest, rSrc1, rSrc2);
        if (ok < 3) {
            // tenta sem vírgula
            ok = sscanf(rest, " %s %s %s", rDest, rSrc1, rSrc2);
        }
        if (ok < 3) {
            strcpy(lastOperationText, instr);
            strcpy(lastExplanationText, "Instrução ADD/SUB inválida.");
            lastInstrCost = 0;
            return;
        }

        int d  = (rDest[1] - '0');
        int s1 = (rSrc1[1] - '0');
        int s2 = (rSrc2[1] - '0');

        int val1=0, val2=0;
        switch(s1){
            case 1: val1=regR1; break;
            case 2: val1=regR2; break;
            case 3: val1=regR3; break;
            case 4: val1=regR4; break;
        }
        switch(s2){
            case 1: val2=regR1; break;
            case 2: val2=regR2; break;
            case 3: val2=regR3; break;
            case 4: val2=regR4; break;
        }

        int result=0;
        if (strcmp(op, "ADD") == 0) {
            result = val1 + val2;
            snprintf(lastOperationText,   MAX_STR_SIZE, "ADD: %s + %s -> %s", rSrc1, rSrc2, rDest);
            snprintf(lastExplanationText, MAX_STR_SIZE, "Soma de %d + %d = %d", val1, val2, result);
        } else {
            // SUB
            result = val1 - val2;
            snprintf(lastOperationText,   MAX_STR_SIZE, "SUB: %s - %s -> %s", rSrc1, rSrc2, rDest);
            snprintf(lastExplanationText, MAX_STR_SIZE, "Subtração de %d - %d = %d", val1, val2, result);
        }

        switch(d){
            case 1: regR1=result; break;
            case 2: regR2=result; break;
            case 3: regR3=result; break;
            case 4: regR4=result; break;
        }
        // ADD/SUB => custo 2
        lastInstrCost = 2;
        totalCycles  += lastInstrCost;

    } else {
        // Nenhum dos 4 opcodes
        strcpy(lastOperationText, instr);
        strcpy(lastExplanationText, "Instrução não reconhecida.");
        lastInstrCost = 0;
    }

    // Atualiza histórico se houver algo em lastOperationText
    if (strlen(lastOperationText) > 0) {
        strcat(historyBuffer, lastOperationText);
        strcat(historyBuffer, "\n");
    }
}

// -----------------------------------------------------------
// Registradores
// -----------------------------------------------------------
DLL_EXPORT const char* getRegistersString(void) {
    static char buf[128];
    snprintf(buf, sizeof(buf),
             "R1=%d, R2=%d, R3=%d, R4=%d",
             regR1, regR2, regR3, regR4);
    return buf;
}

DLL_EXPORT void setRegisterValue(const char* regName, int value) {
    if (!regName) return;
    if (strcmp(regName, "R1") == 0) regR1 = value;
    else if (strcmp(regName, "R2") == 0) regR2 = value;
    else if (strcmp(regName, "R3") == 0) regR3 = value;
    else if (strcmp(regName, "R4") == 0) regR4 = value;
}

// -----------------------------------------------------------
// Memória
// -----------------------------------------------------------
DLL_EXPORT const char* getMemoryString(void) {
    static char buf[256];
    buf[0] = '\0';

    char tmp[32];
    for (int i=0; i<MAX_MEM_SIZE; i++){
        snprintf(tmp, sizeof(tmp), "[%d]: %d", i, memoryData[i]);
        strcat(buf, tmp);
        if (i < MAX_MEM_SIZE-1) {
            strcat(buf, ",");
        }
    }
    return buf;
}

DLL_EXPORT int getMemorySize(void) {
    return MAX_MEM_SIZE;
}

DLL_EXPORT void setMemoryValue(int address, int value) {
    if (address < 0 || address >= MAX_MEM_SIZE) return;
    memoryData[address] = value;
}

DLL_EXPORT int getMemoryValue(int address) {
    if (address < 0 || address >= MAX_MEM_SIZE) return 0;
    return memoryData[address];
}

// -----------------------------------------------------------
// Modo Explicação
// -----------------------------------------------------------
DLL_EXPORT int getExplanationMode(void) {
    return explanationMode;
}
DLL_EXPORT void setExplanationMode(int mode) {
    explanationMode = mode;
}

// -----------------------------------------------------------
// Última operação / explicação
// -----------------------------------------------------------
DLL_EXPORT const char* getLastOperationText(void) {
    return lastOperationText;
}
DLL_EXPORT const char* getLastExplanationText(void) {
    return lastExplanationText;
}

// -----------------------------------------------------------
// Histórico
// -----------------------------------------------------------
DLL_EXPORT void clearHistory(void) {
    strcpy(historyBuffer, "");
}
DLL_EXPORT const char* getHistoryString(void) {
    return historyBuffer;
}

// -----------------------------------------------------------
// Ciclos
// -----------------------------------------------------------
DLL_EXPORT int getTotalCycles(void) {
    return totalCycles;
}
DLL_EXPORT int getLastInstructionCost(void) {
    return lastInstrCost;
}

// -----------------------------------------------------------
// Cache
// -----------------------------------------------------------
DLL_EXPORT int getCacheSize(void) {
    return CACHE_LINES;
}

DLL_EXPORT void getCacheStatus(int* hitsOut, int* missesOut) {
    if (hitsOut)   *hitsOut   = cacheHits;
    if (missesOut) *missesOut = cacheMisses;
}

DLL_EXPORT const char* getCacheLineString(int lineIndex) {
    static char buf[256];
    if (lineIndex < 0 || lineIndex >= CACHE_LINES) {
        snprintf(buf, sizeof(buf), "Linha Inválida");
        return buf;
    }
    CacheLine* c = &cacheLines[lineIndex];
    snprintf(buf, sizeof(buf), "V=%d T=%d D=%d", c->valid, c->tag, c->data);
    return buf;
}

DLL_EXPORT void setCacheLineData(int lineIndex, int newData) {
    if (lineIndex < 0 || lineIndex >= CACHE_LINES) return;
    cacheLines[lineIndex].data = newData;
}

// -----------------------------------------------------------
// Mapeamento (Direto / Associativo)
// -----------------------------------------------------------
DLL_EXPORT void setCacheMappingMode(int mode) {
    if (mode != 0 && mode != 1) {
        mode = 0; // fallback
    }
    mappingMode = mode;
    // Ao mudar, limpa a cache
    invalidateCache();
}
DLL_EXPORT int getCacheMappingMode(void) {
    return mappingMode;
}
