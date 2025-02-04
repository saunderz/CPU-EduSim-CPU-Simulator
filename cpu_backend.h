#ifndef CPU_BACKEND_H
#define CPU_BACKEND_H

#ifdef __cplusplus
extern "C" {
#endif

#ifdef _WIN32
#define DLL_EXPORT __declspec(dllexport)
#else
#define DLL_EXPORT
#endif

// -----------------------------------------------------------
// Inicialização / Reset
// -----------------------------------------------------------
DLL_EXPORT void initCPU(void);
DLL_EXPORT void resetCPU(void);

// -----------------------------------------------------------
// Instruções
// -----------------------------------------------------------
DLL_EXPORT void loadDefaultInstructions(void);
DLL_EXPORT void setInstructions(char* instructions[], int count);
DLL_EXPORT int  getInstructionCount(void);
DLL_EXPORT const char* getInstructionLine(int index);
DLL_EXPORT void nextInstruction(void);

// -----------------------------------------------------------
// Registradores
// -----------------------------------------------------------
DLL_EXPORT const char* getRegistersString(void);
DLL_EXPORT void setRegisterValue(const char* regName, int value);

// -----------------------------------------------------------
// Memória
// -----------------------------------------------------------
DLL_EXPORT const char* getMemoryString(void);
DLL_EXPORT int  getMemorySize(void);
DLL_EXPORT void setMemoryValue(int address, int value);
DLL_EXPORT int  getMemoryValue(int address);

// -----------------------------------------------------------
// Modo Explicação
// -----------------------------------------------------------
DLL_EXPORT int  getExplanationMode(void);
DLL_EXPORT void setExplanationMode(int mode);

// -----------------------------------------------------------
// Última operação e explicação
// -----------------------------------------------------------
DLL_EXPORT const char* getLastOperationText(void);
DLL_EXPORT const char* getLastExplanationText(void);

// -----------------------------------------------------------
// Histórico
// -----------------------------------------------------------
DLL_EXPORT void clearHistory(void);
DLL_EXPORT const char* getHistoryString(void);

// -----------------------------------------------------------
// Ciclos (Clock)
// -----------------------------------------------------------
DLL_EXPORT int  getTotalCycles(void);
DLL_EXPORT int  getLastInstructionCost(void);

// -----------------------------------------------------------
// Cache
// -----------------------------------------------------------
DLL_EXPORT int  getCacheSize(void);
DLL_EXPORT void getCacheStatus(int* hitsOut, int* missesOut);
DLL_EXPORT const char* getCacheLineString(int lineIndex);
DLL_EXPORT void setCacheLineData(int lineIndex, int newData);

// -----------------------------------------------------------
// Mapeamento da Cache (0=direto, 1=associativo)
// -----------------------------------------------------------
DLL_EXPORT void setCacheMappingMode(int mode);
DLL_EXPORT int  getCacheMappingMode(void);

#ifdef __cplusplus
}
#endif

#endif // CPU_BACKEND_H
