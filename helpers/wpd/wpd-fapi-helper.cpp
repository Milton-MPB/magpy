#include <windows.h>
#include <stdio.h>
#include <stdint.h>
#include <objbase.h>
#include <PortableDeviceApi.h>
#include <PortableDevice.h>

const PROPERTYKEY WPD_COMMAND_MTP_EXT_EXECUTE_COMMAND_WITH_DATA_TO_READ =
    { { 0x4d545058, 0x1a2e, 0x4106, { 0xa3, 0x57, 0x77, 0x1e, 0x08, 0x19, 0xfc, 0x56 } }, 12 };
const PROPERTYKEY WPD_COMMAND_MTP_EXT_EXECUTE_COMMAND_WITH_DATA_TO_WRITE =
    { { 0x4d545058, 0x1a2e, 0x4106, { 0xa3, 0x57, 0x77, 0x1e, 0x08, 0x19, 0xfc, 0x56 } }, 13 };
const PROPERTYKEY WPD_PROPERTY_MTP_EXT_OPERATION_CODE =
    { { 0x4d545058, 0x1a2e, 0x4106, { 0xa3, 0x57, 0x77, 0x1e, 0x08, 0x19, 0xfc, 0x56 } }, 1001 };
const PROPERTYKEY WPD_PROPERTY_MTP_EXT_OPERATION_PARAMS =
    { { 0x4d545058, 0x1a2e, 0x4106, { 0xa3, 0x57, 0x77, 0x1e, 0x08, 0x19, 0xfc, 0x56 } }, 1002 };
const PROPERTYKEY WPD_PROPERTY_MTP_EXT_TRANSFER_TOTAL_DATA_SIZE =
    { { 0x4d545058, 0x1a2e, 0x4106, { 0xa3, 0x57, 0x77, 0x1e, 0x08, 0x19, 0xfc, 0x56 } }, 1003 };
const PROPERTYKEY WPD_PROPERTY_MTP_EXT_TRANSFER_DATA =
    { { 0x4d545058, 0x1a2e, 0x4106, { 0xa3, 0x57, 0x77, 0x1e, 0x08, 0x19, 0xfc, 0x56 } }, 1004 };
const PROPERTYKEY WPD_PROPERTY_MTP_EXT_RESPONSE_CODE =
    { { 0x4d545058, 0x1a2e, 0x4106, { 0xa3, 0x57, 0x77, 0x1e, 0x08, 0x19, 0xfc, 0x56 } }, 1006 };

#define OP_SET_DEVICE_PROP      0x1016
#define OP_FAPI_TX              0x9052
#define OP_FAPI_RX              0x9053
#define DPROP_HOST_INFO         0xD406
#define SHUTTER_COUNT_ADDR      0x1015
#define SHUTTER_COUNT_LEN       10

bool isCanonDevice(PWSTR deviceId, IPortableDeviceManager* pManager) {
    WCHAR manufacturer[256] = {0};
    DWORD manufacturerLen = 256;
    if (FAILED(pManager->GetDeviceManufacturer(deviceId, manufacturer, &manufacturerLen))) return false;
    _wcsupr_s(manufacturer, 256);
    return wcsstr(manufacturer, L"CANON") != NULL;
}

HRESULT findCanonCamera(PWSTR* ppDeviceId) {
    IPortableDeviceManager* pManager = NULL;
    HRESULT hr = CoCreateInstance(CLSID_PortableDeviceManager, NULL, CLSCTX_INPROC_SERVER,
                                   IID_IPortableDeviceManager, (VOID**)&pManager);
    if (FAILED(hr)) return hr;

    DWORD deviceCount = 0;
    hr = pManager->GetDevices(NULL, &deviceCount);
    if (FAILED(hr) || deviceCount == 0) { pManager->Release(); return E_FAIL; }

    PWSTR* deviceIds = new PWSTR[deviceCount];
    hr = pManager->GetDevices(deviceIds, &deviceCount);
    if (FAILED(hr)) { delete[] deviceIds; pManager->Release(); return hr; }

    PWSTR foundDeviceId = NULL;
    for (DWORD i = 0; i < deviceCount; i++) {
        if (isCanonDevice(deviceIds[i], pManager)) {
            size_t len = wcslen(deviceIds[i]) + 1;
            foundDeviceId = (PWSTR)CoTaskMemAlloc(len * sizeof(WCHAR));
            wcscpy_s(foundDeviceId, len, deviceIds[i]);
            break;
        }
    }

    for (DWORD i = 0; i < deviceCount; i++) CoTaskMemFree(deviceIds[i]);
    delete[] deviceIds;
    pManager->Release();

    if (foundDeviceId) { *ppDeviceId = foundDeviceId; return S_OK; }
    return E_FAIL;
}

HRESULT SendMtpCommandWithData(IPortableDevice* pDevice, DWORD opcode, DWORD* params,
                                DWORD paramCount, BYTE* data, DWORD dataSize, DWORD* outResponseCode) {
    IPortableDeviceValues* pCommandParams = NULL;
    IPortableDevicePropVariantCollection* pMtpParams = NULL;
    IPortableDeviceValues* pResults = NULL;

    HRESULT hr = CoCreateInstance(CLSID_PortableDeviceValues, NULL, CLSCTX_INPROC_SERVER, IID_IPortableDeviceValues, (VOID**)&pCommandParams);
    if (FAILED(hr)) return hr;

    pCommandParams->SetGuidValue(WPD_PROPERTY_COMMON_COMMAND_CATEGORY, WPD_COMMAND_MTP_EXT_EXECUTE_COMMAND_WITH_DATA_TO_WRITE.fmtid);
    pCommandParams->SetUnsignedIntegerValue(WPD_PROPERTY_COMMON_COMMAND_ID, WPD_COMMAND_MTP_EXT_EXECUTE_COMMAND_WITH_DATA_TO_WRITE.pid);
    pCommandParams->SetUnsignedIntegerValue(WPD_PROPERTY_MTP_EXT_OPERATION_CODE, opcode);
    pCommandParams->SetUnsignedLargeIntegerValue(WPD_PROPERTY_MTP_EXT_TRANSFER_TOTAL_DATA_SIZE, (ULONGLONG)dataSize);

    if (params && paramCount > 0) {
        CoCreateInstance(CLSID_PortableDevicePropVariantCollection, NULL, CLSCTX_INPROC_SERVER, IID_IPortableDevicePropVariantCollection, (VOID**)&pMtpParams);
        for (DWORD i = 0; i < paramCount; i++) {
            PROPVARIANT pv; PropVariantInit(&pv); pv.vt = VT_UI4; pv.ulVal = params[i];
            pMtpParams->Add(&pv);
        }
        pCommandParams->SetIPortableDevicePropVariantCollectionValue(WPD_PROPERTY_MTP_EXT_OPERATION_PARAMS, pMtpParams);
        pMtpParams->Release();
    }

    if (data && dataSize > 0) {
        PROPVARIANT pvData; PropVariantInit(&pvData);
        pvData.vt = VT_VECTOR | VT_UI1; pvData.caub.cElems = dataSize;
        pvData.caub.pElems = (BYTE*)CoTaskMemAlloc(dataSize);
        memcpy(pvData.caub.pElems, data, dataSize);
        pCommandParams->SetValue(WPD_PROPERTY_MTP_EXT_TRANSFER_DATA, &pvData);
        PropVariantClear(&pvData);
    }

    hr = pDevice->SendCommand(0, pCommandParams, &pResults);
    if (SUCCEEDED(hr) && pResults && outResponseCode) {
        pResults->GetUnsignedIntegerValue(WPD_PROPERTY_MTP_EXT_RESPONSE_CODE, outResponseCode);
    }
    if (pResults) pResults->Release();
    pCommandParams->Release();
    return hr;
}

HRESULT ReceiveMtpData(IPortableDevice* pDevice, DWORD opcode, DWORD* params, DWORD paramCount,
                       BYTE* outData, DWORD maxDataSize, DWORD* actualDataSize, DWORD* outResponseCode) {
    IPortableDeviceValues* pCommandParams = NULL;
    IPortableDevicePropVariantCollection* pMtpParams = NULL;
    IPortableDeviceValues* pResults = NULL;

    HRESULT hr = CoCreateInstance(CLSID_PortableDeviceValues, NULL, CLSCTX_INPROC_SERVER, IID_IPortableDeviceValues, (VOID**)&pCommandParams);
    if (FAILED(hr)) return hr;

    pCommandParams->SetGuidValue(WPD_PROPERTY_COMMON_COMMAND_CATEGORY, WPD_COMMAND_MTP_EXT_EXECUTE_COMMAND_WITH_DATA_TO_READ.fmtid);
    pCommandParams->SetUnsignedIntegerValue(WPD_PROPERTY_COMMON_COMMAND_ID, WPD_COMMAND_MTP_EXT_EXECUTE_COMMAND_WITH_DATA_TO_READ.pid);
    pCommandParams->SetUnsignedIntegerValue(WPD_PROPERTY_MTP_EXT_OPERATION_CODE, opcode);
    pCommandParams->SetUnsignedLargeIntegerValue(WPD_PROPERTY_MTP_EXT_TRANSFER_TOTAL_DATA_SIZE, (ULONGLONG)maxDataSize);

    if (params && paramCount > 0) {
        CoCreateInstance(CLSID_PortableDevicePropVariantCollection, NULL, CLSCTX_INPROC_SERVER, IID_IPortableDevicePropVariantCollection, (VOID**)&pMtpParams);
        for (DWORD i = 0; i < paramCount; i++) {
            PROPVARIANT pv; PropVariantInit(&pv); pv.vt = VT_UI4; pv.ulVal = params[i];
            pMtpParams->Add(&pv);
        }
        pCommandParams->SetIPortableDevicePropVariantCollectionValue(WPD_PROPERTY_MTP_EXT_OPERATION_PARAMS, pMtpParams);
        pMtpParams->Release();
    }

    hr = pDevice->SendCommand(0, pCommandParams, &pResults);
    if (SUCCEEDED(hr) && pResults) {
        if (outResponseCode) pResults->GetUnsignedIntegerValue(WPD_PROPERTY_MTP_EXT_RESPONSE_CODE, outResponseCode);
        PROPVARIANT pvData; PropVariantInit(&pvData);
        if (SUCCEEDED(pResults->GetValue(WPD_PROPERTY_MTP_EXT_TRANSFER_DATA, &pvData))) {
            if (pvData.vt == (VT_VECTOR | VT_UI1)) {
                *actualDataSize = min(pvData.caub.cElems, maxDataSize);
                memcpy(outData, pvData.caub.pElems, *actualDataSize);
            }
        }
        PropVariantClear(&pvData);
        pResults->Release();
    }
    pCommandParams->Release();
    return hr;
}

// ---------------------------------------------------------
// PAYLOAD BUILDERS
// ---------------------------------------------------------

void BuildHostInfoPayload(BYTE* buffer, DWORD* outSize) {
    const WCHAR* hostInfo = L"/Windows/10.0.22631 MTPClassDriver/10.0.22621.0";
    size_t len = wcslen(hostInfo);

    // PTP strings require a 1-byte length prefix indicating number of characters (including null)
    buffer[0] = (BYTE)(len + 1);

    // Copy the UTF-16 characters
    memcpy(buffer + 1, hostInfo, len * 2);

    // Add double-null terminator for UTF-16
    buffer[1 + (len * 2)] = 0x00;
    buffer[1 + (len * 2) + 1] = 0x00;

    *outSize = 1 + ((len + 1) * 2); // 1 length byte + (chars + null)*2 bytes
}

void BuildMonOpenPayload(BYTE* buffer, DWORD* outSize) {
    // Captured payload from Wireshark (frame 223):
    // 4d6f6e4f70656e 00  01000000 02000000  [zeros to 36]
    // "MonOpen\0"         field[0] field[1]
    memset(buffer, 0, 128);
    memcpy(buffer, "MonOpen\x00", 8);
    *(uint32_t*)(buffer + 8)  = 0x00000001;  // numFields = 1
    *(uint32_t*)(buffer + 12) = 0x00000002;  // field[0] type = 2
    // Total payload must match exactly what the camera saw in the capture
    *outSize = 36;
}

void BuildMonReadAndGetDataPayload(BYTE* buffer, uint32_t address, uint32_t length, DWORD* outSize) {
    // Exact payload from Wireshark frame 229 (75 bytes total):
    // 4d6f6e52656164416e644765744461746100  = "MonReadAndGetData\0" (18 bytes)
    // 03000000  = 3 (numArgs)
    // 02000000  = 2 (type)
    // 02000000  = 2 (type)
    // 00000000 00000000 00000000 00000000  = padding (16 bytes)
    // 02000000  = 2 (type)
    // [address as uint32 LE]              = e.g. 0x00001015
    // 00000000 00000000 00000000 00000000  = padding (16 bytes)
    // 02000000  = 2 (type)
    // [length as uint32 LE]               = e.g. 0x0000000a
    // [zeros to pad to 75 bytes]
    memset(buffer, 0, 128);

    // String name + null terminator = 18 bytes
    memcpy(buffer, "MonReadAndGetData\x00", 18);

    // Argument header
    *(uint32_t*)(buffer + 18) = 0x00000003;  // numArgs = 3
    *(uint32_t*)(buffer + 22) = 0x00000002;  // arg[0] type
    *(uint32_t*)(buffer + 26) = 0x00000002;  // arg[1] type
    // 16 bytes padding at 30..45

    *(uint32_t*)(buffer + 46) = 0x00000002;  // arg[2] type (address arg)
    *(uint32_t*)(buffer + 50) = address;     // the memory address
    // 16 bytes padding at 54..69

    *(uint32_t*)(buffer + 70) = 0x00000002;  // arg[3] type (length arg)
    *(uint32_t*)(buffer + 74) = length;      // number of bytes to read

    *outSize = 75;  // must be exactly 75, not 86
}

int main() {
    setvbuf(stdout, NULL, _IONBF, 0);
    CoInitializeEx(NULL, COINIT_APARTMENTTHREADED);

    PWSTR deviceId = NULL;
    if (FAILED(findCanonCamera(&deviceId))) {
        printf("{\"success\":false,\"error\":\"No Canon camera found via WPD\"}\n");
        CoUninitialize(); return 1;
    }

    IPortableDevice* pDevice = NULL;
    IPortableDeviceValues* pClientInfo = NULL;
    CoCreateInstance(CLSID_PortableDevice, NULL, CLSCTX_INPROC_SERVER, IID_IPortableDevice, (VOID**)&pDevice);
    CoCreateInstance(CLSID_PortableDeviceValues, NULL, CLSCTX_INPROC_SERVER, IID_IPortableDeviceValues, (VOID**)&pClientInfo);

    pClientInfo->SetStringValue(WPD_CLIENT_NAME, L"MagPy FAPI Reader");
    pClientInfo->SetUnsignedIntegerValue(WPD_CLIENT_MAJOR_VERSION, 1);
    pClientInfo->SetUnsignedIntegerValue(WPD_CLIENT_DESIRED_ACCESS, GENERIC_READ | GENERIC_WRITE);

    if (FAILED(pDevice->Open(deviceId, pClientInfo))) {
        printf("{\"success\":false,\"error\":\"Failed to open WPD device with WRITE access\"}\n");
        return 1;
    }

    DWORD responseCode = 0;
    DWORD payloadSize;
    BYTE payload[128];

    // Step 0: The Missing Handshake (Unlock the Camera)
    DWORD propParams[1] = { DPROP_HOST_INFO };
    BuildHostInfoPayload(payload, &payloadSize);
    SendMtpCommandWithData(pDevice, OP_SET_DEVICE_PROP, propParams, 1, payload, payloadSize, &responseCode);
    fprintf(stderr, "[DEBUG] Handshake Response Code: 0x%04X\n", responseCode);

    // Step 1: MonOpen — send payload, then drain the response with FAPI_RX
    DWORD fapiParams[2] = {0x00000000, 0x00000000};
    BuildMonOpenPayload(payload, &payloadSize);
    SendMtpCommandWithData(pDevice, OP_FAPI_TX, fapiParams, 2, payload, payloadSize, &responseCode);
    fprintf(stderr, "[DEBUG] MonOpen TX Response Code: 0x%04X\n", responseCode);

    // Drain the MonOpen response — camera sends back a result on 0x9053 that must be consumed
    {
        BYTE drainBuf[256] = {0};
        DWORD drainSize = 0;
        DWORD drainCode = 0;
        DWORD drainParams[3] = {0x00000000, 0x00000000, 0x00000000};
        ReceiveMtpData(pDevice, OP_FAPI_RX, drainParams, 3, drainBuf, 256, &drainSize, &drainCode);
        fprintf(stderr, "[DEBUG] MonOpen RX drain: code=0x%04X bytes=%lu\n", drainCode, drainSize);
    }

    // Step 2: MonReadAndGetData — send payload, then drain its response too
    DWORD fapiParamsRead[2] = {0x00000000, 0x00000001};
    BuildMonReadAndGetDataPayload(payload, SHUTTER_COUNT_ADDR, SHUTTER_COUNT_LEN, &payloadSize);
    SendMtpCommandWithData(pDevice, OP_FAPI_TX, fapiParamsRead, 2, payload, payloadSize, &responseCode);
    fprintf(stderr, "[DEBUG] MonRead TX Response Code: 0x%04X\n", responseCode);

    Sleep(150);

    // Step 3: FAPI_RX — read the actual shutter count data
    BYTE responseData[8192] = {0};
    DWORD actualDataSize = 0;
    DWORD fapiRxParams[3] = {0x00000000, 0x00000000, 0x00000001};

    ReceiveMtpData(pDevice, OP_FAPI_RX, fapiRxParams, 3, responseData, 8192, &actualDataSize, &responseCode);
    fprintf(stderr, "[DEBUG] FAPI_RX Response Code: 0x%04X. Bytes Read: %lu\n", responseCode, actualDataSize);

    // Step 4: MonClose — always close the monitor, even on failure
    {
        BYTE closePayload[128];
        DWORD closeSize;
        DWORD closeCode = 0;
        DWORD closeParams[2] = {0x00000000, 0x00000000};
        memset(closePayload, 0, 128);
        memcpy(closePayload, "MonClose\x00", 9);
        *(uint32_t*)(closePayload + 9)  = 0x00000001;
        *(uint32_t*)(closePayload + 13) = 0x00000002;
        closeSize = 36;
        SendMtpCommandWithData(pDevice, OP_FAPI_TX, closeParams, 2, closePayload, closeSize, &closeCode);
        fprintf(stderr, "[DEBUG] MonClose Response Code: 0x%04X\n", closeCode);
    }

    if (responseCode != 0x2001 || actualDataSize < 10) {
        printf("{\"success\":false,\"error\":\"Camera rejected command. Code: 0x%04X, Bytes: %lu\"}\n", responseCode, actualDataSize);
        return 1;
    }

    uint32_t mechanical = *(uint32_t*)(responseData + 0);
    uint32_t electronic = *(uint32_t*)(responseData + 6);
    uint32_t total = mechanical + electronic;

    printf("{\"success\":true,\"mechanical\":%u,\"electronic\":%u,\"total\":%u,\"source\":\"WPD FAPI\"}\n",
           mechanical, electronic, total);

    if (pClientInfo) pClientInfo->Release();
    if (pDevice) pDevice->Release();
    if (deviceId) CoTaskMemFree(deviceId);
    CoUninitialize();

    return 0;
}
