#include <windows.h>
#include <stdio.h>
#include <stdint.h>
#include <objbase.h>
#include <PortableDeviceApi.h>
#include <PortableDevice.h>

// WPD MTP Pass-Through Command GUIDs
const PROPERTYKEY WPD_COMMAND_MTP_EXT_EXECUTE_COMMAND_WITHOUT_DATA_PHASE =
    { { 0x4d545058, 0x1a2e, 0x4106, { 0xa3, 0x57, 0x77, 0x1e, 0x08, 0x19, 0xfc, 0x56 } }, 11 };
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

// Canon PTP OpCodes
#define OP_FAPI_TX              0x9052
#define OP_FAPI_RX              0x9053

// Shutter count memory address
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
    if (FAILED(hr) || deviceCount == 0) {
        pManager->Release();
        return E_FAIL;
    }

    PWSTR* deviceIds = new PWSTR[deviceCount];
    hr = pManager->GetDevices(deviceIds, &deviceCount);
    if (FAILED(hr)) {
        delete[] deviceIds;
        pManager->Release();
        return hr;
    }

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

    if (foundDeviceId) {
        *ppDeviceId = foundDeviceId;
        return S_OK;
    }
    return E_FAIL;
}

HRESULT SendMtpCommandWithData(IPortableDevice* pDevice, DWORD opcode, DWORD* params,
                                DWORD paramCount, BYTE* data, DWORD dataSize) {
    IPortableDeviceValues* pCommandParams = NULL;
    IPortableDevicePropVariantCollection* pMtpParams = NULL;
    IPortableDeviceValues* pResults = NULL;

    HRESULT hr = CoCreateInstance(CLSID_PortableDeviceValues, NULL, CLSCTX_INPROC_SERVER,
                                   IID_IPortableDeviceValues, (VOID**)&pCommandParams);
    if (FAILED(hr)) return hr;

    pCommandParams->SetGuidValue(WPD_PROPERTY_COMMON_COMMAND_CATEGORY,
                                  WPD_COMMAND_MTP_EXT_EXECUTE_COMMAND_WITH_DATA_TO_WRITE.fmtid);
    pCommandParams->SetUnsignedIntegerValue(WPD_PROPERTY_COMMON_COMMAND_ID,
                                             WPD_COMMAND_MTP_EXT_EXECUTE_COMMAND_WITH_DATA_TO_WRITE.pid);
    pCommandParams->SetUnsignedIntegerValue(WPD_PROPERTY_MTP_EXT_OPERATION_CODE, opcode);

    if (params && paramCount > 0) {
        hr = CoCreateInstance(CLSID_PortableDevicePropVariantCollection, NULL, CLSCTX_INPROC_SERVER,
                              IID_IPortableDevicePropVariantCollection, (VOID**)&pMtpParams);
        if (SUCCEEDED(hr)) {
            for (DWORD i = 0; i < paramCount; i++) {
                PROPVARIANT pv;
                PropVariantInit(&pv);
                pv.vt = VT_UI4;
                pv.ulVal = params[i];
                pMtpParams->Add(&pv);
            }
            pCommandParams->SetIPortableDevicePropVariantCollectionValue(
                WPD_PROPERTY_MTP_EXT_OPERATION_PARAMS, pMtpParams);
            pMtpParams->Release();
        }
    }

    if (data && dataSize > 0) {
        PROPVARIANT pvData;
        PropVariantInit(&pvData);
        pvData.vt = VT_VECTOR | VT_UI1;
        pvData.caub.cElems = dataSize;
        pvData.caub.pElems = (BYTE*)CoTaskMemAlloc(dataSize);
        memcpy(pvData.caub.pElems, data, dataSize);
        pCommandParams->SetValue(WPD_PROPERTY_MTP_EXT_TRANSFER_DATA, &pvData);
        PropVariantClear(&pvData);
    }

    hr = pDevice->SendCommand(0, pCommandParams, &pResults);
    if (pResults) pResults->Release();
    pCommandParams->Release();
    return hr;
}

HRESULT ReceiveMtpData(IPortableDevice* pDevice, DWORD opcode, DWORD* params, DWORD paramCount,
                       BYTE* outData, DWORD maxDataSize, DWORD* actualDataSize) {
    IPortableDeviceValues* pCommandParams = NULL;
    IPortableDevicePropVariantCollection* pMtpParams = NULL;
    IPortableDeviceValues* pResults = NULL;

    HRESULT hr = CoCreateInstance(CLSID_PortableDeviceValues, NULL, CLSCTX_INPROC_SERVER,
                                   IID_IPortableDeviceValues, (VOID**)&pCommandParams);
    if (FAILED(hr)) return hr;

    pCommandParams->SetGuidValue(WPD_PROPERTY_COMMON_COMMAND_CATEGORY,
                                  WPD_COMMAND_MTP_EXT_EXECUTE_COMMAND_WITH_DATA_TO_READ.fmtid);
    pCommandParams->SetUnsignedIntegerValue(WPD_PROPERTY_COMMON_COMMAND_ID,
                                             WPD_COMMAND_MTP_EXT_EXECUTE_COMMAND_WITH_DATA_TO_READ.pid);
    pCommandParams->SetUnsignedIntegerValue(WPD_PROPERTY_MTP_EXT_OPERATION_CODE, opcode);

    // THE FIX: Explicitly tell Windows how many bytes we want to read
    pCommandParams->SetUnsignedLargeIntegerValue(WPD_PROPERTY_MTP_EXT_TRANSFER_TOTAL_DATA_SIZE, (ULONGLONG)maxDataSize);

    if (params && paramCount > 0) {
        hr = CoCreateInstance(CLSID_PortableDevicePropVariantCollection, NULL, CLSCTX_INPROC_SERVER,
                              IID_IPortableDevicePropVariantCollection, (VOID**)&pMtpParams);
        if (SUCCEEDED(hr)) {
            for (DWORD i = 0; i < paramCount; i++) {
                PROPVARIANT pv;
                PropVariantInit(&pv);
                pv.vt = VT_UI4;
                pv.ulVal = params[i];
                pMtpParams->Add(&pv);
            }
            pCommandParams->SetIPortableDevicePropVariantCollectionValue(
                WPD_PROPERTY_MTP_EXT_OPERATION_PARAMS, pMtpParams);
            pMtpParams->Release();
        }
    }

    hr = pDevice->SendCommand(0, pCommandParams, &pResults);
    if (SUCCEEDED(hr) && pResults) {
        PROPVARIANT pvData;
        PropVariantInit(&pvData);
        if (SUCCEEDED(pResults->GetValue(WPD_PROPERTY_MTP_EXT_TRANSFER_DATA, &pvData))) {
            if (pvData.vt == (VT_VECTOR | VT_UI1)) {
                DWORD dataSize = min(pvData.caub.cElems, maxDataSize);
                memcpy(outData, pvData.caub.pElems, dataSize);
                *actualDataSize = dataSize;
            }
        }
        PropVariantClear(&pvData);
        pResults->Release();
    }
    pCommandParams->Release();
    return hr;
}

void BuildMonOpenPayload(BYTE* buffer, DWORD* outSize) {
    memset(buffer, 0, 128);
    memcpy(buffer, "MonOpen\x00", 8);
    *(uint32_t*)(buffer + 8) = 0x00000001;
    *(uint32_t*)(buffer + 12) = 0x00000002;
    *outSize = 60;
}

void BuildMonReadAndGetDataPayload(BYTE* buffer, uint32_t address, uint32_t length, DWORD* outSize) {
    memset(buffer, 0, 128);
    memcpy(buffer, "MonReadAndGetData\x00", 18);

    *(uint32_t*)(buffer + 18) = 0x00000003;
    *(uint32_t*)(buffer + 22) = 0x00000002;
    *(uint32_t*)(buffer + 26) = 0x00000002;

    *(uint32_t*)(buffer + 42) = 0x00000002;
    *(uint32_t*)(buffer + 46) = address;

    *(uint32_t*)(buffer + 62) = 0x00000002;
    *(uint32_t*)(buffer + 66) = length;
    *outSize = 82;
}

void BuildMonClosePayload(BYTE* buffer, DWORD* outSize) {
    memset(buffer, 0, 128);
    memcpy(buffer, "MonClose\x00", 9);
    *(uint32_t*)(buffer + 9) = 0x00000001;
    *(uint32_t*)(buffer + 13) = 0x00000002;
    *outSize = 60;
}

int main() {
    setvbuf(stdout, NULL, _IONBF, 0);
    CoInitializeEx(NULL, COINIT_APARTMENTTHREADED);

    PWSTR deviceId = NULL;
    HRESULT hr = findCanonCamera(&deviceId);
    if (FAILED(hr)) {
        printf("{\"success\":false,\"error\":\"No Canon camera found via WPD\"}\n");
        CoUninitialize();
        return 1;
    }

    IPortableDevice* pDevice = NULL;
    IPortableDeviceValues* pClientInfo = NULL;

    CoCreateInstance(CLSID_PortableDevice, NULL, CLSCTX_INPROC_SERVER, IID_IPortableDevice, (VOID**)&pDevice);
    CoCreateInstance(CLSID_PortableDeviceValues, NULL, CLSCTX_INPROC_SERVER, IID_IPortableDeviceValues, (VOID**)&pClientInfo);

    pClientInfo->SetStringValue(WPD_CLIENT_NAME, L"MagPy FAPI Reader");
    pClientInfo->SetUnsignedIntegerValue(WPD_CLIENT_MAJOR_VERSION, 1);

    hr = pDevice->Open(deviceId, pClientInfo);
    if (FAILED(hr)) {
        printf("{\"success\":false,\"error\":\"Failed to open WPD device\"}\n");
        return 1;
    }

    // Step 1: MonOpen
    BYTE monOpenPayload[128];
    DWORD payloadSize;
    BuildMonOpenPayload(monOpenPayload, &payloadSize);

    DWORD fapiParams[2] = {0x00000000, 0x00000000};
    hr = SendMtpCommandWithData(pDevice, OP_FAPI_TX, fapiParams, 2, monOpenPayload, payloadSize);
    if (FAILED(hr)) {
        printf("{\"success\":false,\"error\":\"MonOpen failed\"}\n");
        return 1;
    }

    // Step 2: MonReadAndGetData (Address 0x1015)
    BYTE monReadPayload[128];
    BuildMonReadAndGetDataPayload(monReadPayload, SHUTTER_COUNT_ADDR, SHUTTER_COUNT_LEN, &payloadSize);

    DWORD fapiParamsRead[2] = {0x00000000, 0x00000001};
    hr = SendMtpCommandWithData(pDevice, OP_FAPI_TX, fapiParamsRead, 2, monReadPayload, payloadSize);
    if (FAILED(hr)) {
        printf("{\"success\":false,\"error\":\"MonReadAndGetData failed\"}\n");
        return 1;
    }

    // Give the camera processor a fraction of a second to fetch memory
    Sleep(100);

    // Step 3: FAPI_RX to get the response data
    BYTE responseData[8192] = {0};
    DWORD actualDataSize = 0;

    DWORD fapiRxParams[3] = {0x00000000, 0x00000000, 0x00000001};
    hr = ReceiveMtpData(pDevice, OP_FAPI_RX, fapiRxParams, 3, responseData, sizeof(responseData), &actualDataSize);

    if (FAILED(hr) || actualDataSize < 10) {
        printf("{\"success\":false,\"error\":\"FAPI_RX failed. Received %lu bytes.\"}\n", actualDataSize);
        return 1;
    }

    // Parse shutter count
    uint32_t mechanical = *(uint32_t*)(responseData + 0);
    uint32_t electronic = *(uint32_t*)(responseData + 6);
    uint32_t total = mechanical + electronic;

    // Step 4: MonClose
    BYTE monClosePayload[128];
    BuildMonClosePayload(monClosePayload, &payloadSize);
    SendMtpCommandWithData(pDevice, OP_FAPI_TX, fapiParams, 2, monClosePayload, payloadSize);

    // Output result
    printf("{\"success\":true,\"mechanical\":%u,\"electronic\":%u,\"total\":%u,\"source\":\"WPD FAPI\"}\n",
           mechanical, electronic, total);

    // Cleanup
    if (pClientInfo) pClientInfo->Release();
    if (pDevice) pDevice->Release();
    if (deviceId) CoTaskMemFree(deviceId);
    CoUninitialize();

    return 0;
}
