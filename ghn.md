curl 'https://fe-online-gateway.ghn.vn/order-tracking/public-api/client/tracking-logs' \
  -H 'accept: application/json' \
  -H 'accept-language: en-US,en;q=0.7' \
  -H 'cache-control: no-cache' \
  -H 'content-type: application/json' \
  -H 'origin: https://donhang.ghn.vn' \
  -H 'pragma: no-cache' \
  -H 'priority: u=1, i' \
  -H 'referer: https://donhang.ghn.vn/' \
  -H 'sec-ch-ua: "Brave";v="147", "Not.A/Brand";v="8", "Chromium";v="147"' \
  -H 'sec-ch-ua-mobile: ?0' \
  -H 'sec-ch-ua-platform: "macOS"' \
  -H 'sec-fetch-dest: empty' \
  -H 'sec-fetch-mode: cors' \
  -H 'sec-fetch-site: same-site' \
  -H 'sec-gpc: 1' \
  -H 'token: [object Object]' \
  -H 'user-agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36' \
  --data-raw '{"order_code":"GYKEQFDX"}'

{
    "code": 200,
    "message": "Success",
    "data": {
        "order_info": {
            "order_code": "GYKEQFDX",
            "client_order_code": "5938920630166535394",
            "shop_id": 6192940,
            "status": "returned",
            "action": "RETURN_IN_TRIP",
            "status_name": "Hoàn hàng thành công",
            "picktime": "2026-04-14T00:46:38.159Z",
            "leadtime": "2026-04-19T16:59:59Z",
            "leadtime_order": {
                "from_estimate_date": "2026-04-19T16:59:59Z",
                "to_estimate_date": "2026-04-20T16:59:59Z",
                "picked_date": "2026-04-14T10:02:11.826Z",
                "returned_date": "2026-04-19T13:36:29.083Z"
            },
            "finish_date": "2026-04-19T13:36:29.083Z",
            "to_name": "xxxx ựt\u003c\u003e",
            "to_phone": "xxxx 3408",
            "to_address": "xxxx Huyện Mỏ Cày Nam Bến Tre",
            "from_name": "xxxx  Kem",
            "from_phone": "xxxx 2815",
            "from_address": "xxxx Huyện Sóc Sơn Hà Nội",
            "return_name": "xxxx  Kem",
            "return_phone": "xxxx 2815",
            "return_address": "xxxx  Nội",
            "payment_type_id": 1,
            "order_version": "corev2",
            "is_partial_return": false,
            "danger_zone_sender": false,
            "danger_zone_deliver": false,
            "sub": 6,
            "is_sss": true,
            "items": null,
            "is_sensitive_data": false
        },
        "tracking_logs": [
            {
                "order_code": "GYKEQFDX",
                "status": "ready_to_pick",
                "status_name": "Chờ lấy hàng",
                "location": {
                    "address": "xxxx Huyện Sóc Sơn Hà Nội",
                    "ward_code": "560909",
                    "district_id": 1975,
                    "warehouse_id": 20108000
                },
                "executor": {
                    "client_id": 3892833,
                    "name": "xxxx lky ",
                    "phone": "xxxx 6680"
                },
                "action_at": "2026-04-14T00:46:38.158Z",
                "sync_data_at": null
            },
            {
                "order_code": "GYKEQFDX",
                "action_code": "START_PICKING_TRIP",
                "status": "picking",
                "status_name": "Đang lấy hàng",
                "location": {
                    "address": "Nhân viên đang lấy hàng tại địa chỉ xxxx Huyện Sóc Sơn Hà Nội",
                    "ward_code": "560909",
                    "district_id": 1975,
                    "warehouse_id": 20108000
                },
                "executor": {
                    "employee_id": 3125392,
                    "name": "xxxx  Chi",
                    "phone": "xxxx 7558"
                },
                "action_at": "2026-04-14T00:48:54.23Z",
                "sync_data_at": null
            },
            {
                "order_code": "GYKEQFDX",
                "action_code": "PICKED_IN_TRIP",
                "status": "picked",
                "status_name": "Lấy hàng thành công",
                "location": {
                    "address": "Đơn hàng lấy thành công tại xxxx Huyện Sóc Sơn Hà Nội",
                    "ward_code": "560909",
                    "district_id": 1975,
                    "warehouse_id": 20108000
                },
                "executor": {
                    "employee_id": 3125392,
                    "name": "xxxx  Chi",
                    "phone": "xxxx 7558"
                },
                "action_at": "2026-04-14T10:02:11.847Z",
                "sync_data_at": null
            },
            {
                "order_code": "GYKEQFDX",
                "action_code": "SCAN_TO_STORING",
                "status": "picked_to_storing",
                "status_name": "Nhập bưu cục lấy",
                "location": {
                    "address": "Đơn hàng lưu tại Bưu Cục 39 Gò Sỏi-Sóc Sơn-HN",
                    "ward_code": "560909",
                    "district_id": 1975,
                    "warehouse_id": 20108000
                },
                "executor": {
                    "employee_id": 3000037,
                    "name": "xxxx Châm",
                    "phone": "xxxx 5451"
                },
                "action_at": "2026-04-14T12:27:51.322Z",
                "sync_data_at": null
            },
            {
                "order_code": "GYKEQFDX",
                "action_code": "PACKED_TO_SORTING",
                "status": "storing",
                "status_name": "Sẵn sàng xuất đến Kho trung chuyển",
                "location": {
                    "address": "Đơn hàng chờ xuất đến Kho Trung Chuyển Hồ Chí Minh 01",
                    "ward_code": "560909",
                    "district_id": 1975,
                    "warehouse_id": 20108000,
                    "next_warehouse_id": 1626
                },
                "executor": {
                    "employee_id": 3000037,
                    "name": "xxxx Châm",
                    "phone": "xxxx 5451"
                },
                "action_at": "2026-04-14T12:27:51.435Z",
                "sync_data_at": null
            },
            {
                "order_code": "GYKEQFDX",
                "action_code": "TRANSFER_TO_TRUCK",
                "status": "storing",
                "status_name": "Xuất hàng đi khỏi kho",
                "location": {
                    "address": "Đơn hàng đã xuất khỏi Bưu Cục 39 Gò Sỏi-Sóc Sơn-HN đến Kho Trung Chuyển Hồ Chí Minh 01",
                    "ward_code": "560909",
                    "district_id": 1975,
                    "warehouse_id": 20108000,
                    "next_warehouse_id": 1626
                },
                "executor": {
                    "employee_id": 3000037,
                    "name": "xxxx Châm",
                    "phone": "xxxx 5451"
                },
                "action_at": "2026-04-14T12:38:54.842Z",
                "sync_data_at": null
            },
            {
                "order_code": "GYKEQFDX",
                "action_code": "TRANSPORTING",
                "status": "transporting",
                "status_name": "Đang trung chuyển hàng",
                "location": {
                    "address": "Đơn hàng đang trung chuyển đến Kho Trung Chuyển Hồ Chí Minh 01",
                    "ward_code": "560909",
                    "district_id": 1975,
                    "warehouse_id": 20108000,
                    "next_warehouse_id": 1626
                },
                "executor": {
                    "employee_id": 8888
                },
                "action_at": "2026-04-14T12:40:19.928Z",
                "sync_data_at": null
            },
            {
                "order_code": "GYKEQFDX",
                "action_code": "ARRIVE_AT_SORTING",
                "status": "transporting",
                "status_name": "Đang trung chuyển hàng",
                "location": {
                    "address": "Đơn hàng đang trung chuyển đến Kho Trung Chuyển Hồ Chí Minh 01",
                    "ward_code": "560909",
                    "district_id": 1975,
                    "warehouse_id": 1121,
                    "next_warehouse_id": 1626
                },
                "executor": {
                    "employee_id": 8888
                },
                "action_at": "2026-04-14T13:40:35.3Z",
                "sync_data_at": null
            },
            {
                "order_code": "GYKEQFDX",
                "action_code": "RECEIVED_AT_SORTING",
                "status": "transporting",
                "status_name": "Nhập hàng vào kho trung chuyển",
                "location": {
                    "address": "Đơn hàng lưu tại Kho Trung Chuyển Hà Nội 02",
                    "ward_code": "560909",
                    "district_id": 1975,
                    "warehouse_id": 1121,
                    "next_warehouse_id": 1626
                },
                "executor": {
                    "employee_id": 3112374,
                    "name": "xxxx  Hợp",
                    "phone": "xxxx 8032"
                },
                "action_at": "2026-04-14T14:31:36.179Z",
                "sync_data_at": null
            },
            {
                "order_code": "GYKEQFDX",
                "action_code": "TRANSFER_TO_TRUCK",
                "status": "transporting",
                "status_name": "Xuất hàng đi khỏi kho",
                "location": {
                    "address": "Đơn hàng đã xuất khỏi Kho Trung Chuyển Hà Nội 02 đến Kho Trung Chuyển Hồ Chí Minh 01",
                    "ward_code": "560909",
                    "district_id": 1975,
                    "warehouse_id": 1121,
                    "next_warehouse_id": 1626
                },
                "executor": {
                    "employee_id": 3131691,
                    "name": "xxxx hắng",
                    "phone": "xxxx 5184"
                },
                "action_at": "2026-04-14T17:24:21.251Z",
                "sync_data_at": null
            },
            {
                "order_code": "GYKEQFDX",
                "action_code": "TRANSPORTING",
                "status": "transporting",
                "status_name": "Đang trung chuyển hàng",
                "location": {
                    "address": "Đơn hàng đang trung chuyển đến Kho Trung Chuyển Hồ Chí Minh 01",
                    "ward_code": "560909",
                    "district_id": 1975,
                    "warehouse_id": 1121,
                    "next_warehouse_id": 1626
                },
                "executor": {
                    "employee_id": 8888
                },
                "action_at": "2026-04-14T17:30:23.643Z",
                "sync_data_at": null
            },
            {
                "order_code": "GYKEQFDX",
                "action_code": "ARRIVE_AT_SORTING",
                "status": "transporting",
                "status_name": "Đang trung chuyển hàng",
                "location": {
                    "address": "Đơn hàng đang trung chuyển đến Kho Trung Chuyển Hồ Chí Minh 01",
                    "ward_code": "560909",
                    "district_id": 1975,
                    "warehouse_id": 1626,
                    "next_warehouse_id": 1626
                },
                "executor": {
                    "employee_id": 8888
                },
                "action_at": "2026-04-16T01:42:29.083Z",
                "sync_data_at": null
            },
            {
                "order_code": "GYKEQFDX",
                "action_code": "RECEIVED_AT_SORTING",
                "status": "transporting",
                "status_name": "Nhập hàng vào kho trung chuyển",
                "location": {
                    "address": "Đơn hàng lưu tại Kho Trung Chuyển Hồ Chí Minh 01",
                    "ward_code": "560909",
                    "district_id": 1975,
                    "warehouse_id": 1626,
                    "next_warehouse_id": 1626
                },
                "executor": {
                    "employee_id": 3090114,
                    "name": "xxxx ường",
                    "phone": "xxxx 9840"
                },
                "action_at": "2026-04-16T02:00:09.811Z",
                "sync_data_at": null
            },
            {
                "order_code": "GYKEQFDX",
                "action_code": "UNPACKED_AT_SORTING",
                "status": "transporting",
                "status_name": "Đang trung chuyển hàng",
                "location": {
                    "address": "Đơn hàng đang trung chuyển đến Kho Trung Chuyển Hồ Chí Minh 01",
                    "ward_code": "560909",
                    "district_id": 1975,
                    "warehouse_id": 1626,
                    "next_warehouse_id": 1626
                },
                "executor": {
                    "employee_id": 3090114,
                    "name": "xxxx ường",
                    "phone": "xxxx 9840"
                },
                "action_at": "2026-04-16T02:00:09.886Z",
                "sync_data_at": null
            },
            {
                "order_code": "GYKEQFDX",
                "action_code": "UNPACKED_AT_SORTING",
                "status": "storing",
                "status_name": "Đang phân loại hàng",
                "location": {
                    "address": "Đơn hàng đang phân loại tại Kho Trung Chuyển Hồ Chí Minh 01",
                    "ward_code": "560909",
                    "district_id": 1975,
                    "warehouse_id": 1626,
                    "next_warehouse_id": 1626
                },
                "executor": {
                    "employee_id": 3090114,
                    "name": "xxxx ường",
                    "phone": "xxxx 9840"
                },
                "action_at": "2026-04-16T02:00:09.923Z",
                "sync_data_at": null
            },
            {
                "order_code": "GYKEQFDX",
                "action_code": "PACKED_TO_LASTMILE",
                "status": "storing",
                "status_name": "Sẵn sàng xuất đến bưu cục giao",
                "location": {
                    "address": "Đơn hàng chờ xuất đến Bưu Cục Mỏ Cày Nam-Bến Tre",
                    "ward_code": "560909",
                    "district_id": 1975,
                    "warehouse_id": 1626,
                    "next_warehouse_id": 1934
                },
                "executor": {
                    "employee_id": 3090114,
                    "name": "xxxx ường",
                    "phone": "xxxx 9840"
                },
                "action_at": "2026-04-16T02:00:09.991Z",
                "sync_data_at": null
            },
            {
                "order_code": "GYKEQFDX",
                "action_code": "TRANSFER_TO_TRUCK",
                "status": "storing",
                "status_name": "Xuất hàng đi khỏi kho",
                "location": {
                    "address": "Đơn hàng đã xuất khỏi Kho Trung Chuyển Hồ Chí Minh 01 đến Bưu Cục Mỏ Cày Nam-Bến Tre",
                    "ward_code": "560909",
                    "district_id": 1975,
                    "warehouse_id": 1626,
                    "next_warehouse_id": 1934
                },
                "executor": {
                    "employee_id": 3148208,
                    "name": "xxxx  Tâm",
                    "phone": "xxxx 1838"
                },
                "action_at": "2026-04-16T03:56:07.162Z",
                "sync_data_at": null
            },
            {
                "order_code": "GYKEQFDX",
                "action_code": "TRANSPORTING",
                "status": "transporting",
                "status_name": "Đang trung chuyển hàng",
                "location": {
                    "address": "Đơn hàng đang trung chuyển đến Bưu Cục Mỏ Cày Nam-Bến Tre",
                    "ward_code": "560909",
                    "district_id": 1975,
                    "warehouse_id": 1626,
                    "next_warehouse_id": 1934
                },
                "executor": {
                    "employee_id": 8888
                },
                "action_at": "2026-04-16T03:57:27.778Z",
                "sync_data_at": null
            },
            {
                "order_code": "GYKEQFDX",
                "action_code": "ARRIVE_AT_LASTMILE",
                "status": "transporting",
                "status_name": "Đang trung chuyển hàng",
                "location": {
                    "address": "Đơn hàng đang trung chuyển đến Bưu Cục Mỏ Cày Nam-Bến Tre",
                    "ward_code": "560909",
                    "district_id": 1975,
                    "warehouse_id": 1934,
                    "next_warehouse_id": 1934
                },
                "executor": {
                    "employee_id": 8888
                },
                "action_at": "2026-04-16T06:11:13.936Z",
                "sync_data_at": null
            },
            {
                "order_code": "GYKEQFDX",
                "action_code": "RECEIVED_AT_LASTMILE",
                "status": "transporting",
                "status_name": "Nhập hàng vào bưu cục giao",
                "location": {
                    "address": "Đơn hàng lưu tại Bưu Cục Mỏ Cày Nam-Bến Tre",
                    "ward_code": "560909",
                    "district_id": 1975,
                    "warehouse_id": 1934,
                    "next_warehouse_id": 1934
                },
                "executor": {
                    "employee_id": 3004516,
                    "name": "xxxx ường",
                    "phone": "xxxx 3839"
                },
                "action_at": "2026-04-16T06:14:20.291Z",
                "sync_data_at": null
            },
            {
                "order_code": "GYKEQFDX",
                "action_code": "UNPACKED_AT_LASTMILE",
                "status": "transporting",
                "status_name": "Đang trung chuyển hàng",
                "location": {
                    "address": "Đơn hàng đang trung chuyển đến Bưu Cục Mỏ Cày Nam-Bến Tre",
                    "ward_code": "560909",
                    "district_id": 1975,
                    "warehouse_id": 1934,
                    "next_warehouse_id": 1934
                },
                "executor": {
                    "employee_id": 3004516,
                    "name": "xxxx ường",
                    "phone": "xxxx 3839"
                },
                "action_at": "2026-04-16T06:14:20.346Z",
                "sync_data_at": null
            },
            {
                "order_code": "GYKEQFDX",
                "action_code": "UNPACKED_AT_LASTMILE",
                "status": "storing",
                "status_name": "Sẵn sàng giao hàng",
                "location": {
                    "address": "Đơn hàng sẵn sàng được giao tại Bưu Cục Mỏ Cày Nam-Bến Tre",
                    "ward_code": "560909",
                    "district_id": 1975,
                    "warehouse_id": 1934,
                    "next_warehouse_id": 1934
                },
                "executor": {
                    "employee_id": 3004516,
                    "name": "xxxx ường",
                    "phone": "xxxx 3839"
                },
                "action_at": "2026-04-16T06:14:20.382Z",
                "sync_data_at": null
            },
            {
                "order_code": "GYKEQFDX",
                "action_code": "RECEIVED_AT_LASTMILE",
                "status": "storing",
                "status_name": "Nhập hàng vào bưu cục giao",
                "location": {
                    "address": "Đơn hàng lưu tại Bưu Cục Mỏ Cày Nam-Bến Tre",
                    "ward_code": "560909",
                    "district_id": 1975,
                    "warehouse_id": 1934,
                    "next_warehouse_id": 1934
                },
                "executor": {
                    "employee_id": 3004516,
                    "name": "xxxx ường",
                    "phone": "xxxx 3839"
                },
                "action_at": "2026-04-16T06:14:20.553Z",
                "sync_data_at": null
            },
            {
                "order_code": "GYKEQFDX",
                "action_code": "ADD_DELIVERY_TRIP",
                "status": "storing",
                "status_name": "Sẵn sàng giao hàng",
                "location": {
                    "address": "Đơn hàng sẵn sàng được giao tại Bưu Cục Mỏ Cày Nam-Bến Tre",
                    "ward_code": "560909",
                    "district_id": 1975,
                    "warehouse_id": 1934,
                    "next_warehouse_id": 1934
                },
                "executor": {
                    "employee_id": 3004516,
                    "name": "xxxx ường",
                    "phone": "xxxx 3839"
                },
                "action_at": "2026-04-16T06:19:49.142Z",
                "sync_data_at": null
            },
            {
                "order_code": "GYKEQFDX",
                "action_code": "START_DELIVERY_TRIP",
                "status": "delivering",
                "status_name": "Đang giao hàng lần 1",
                "location": {
                    "address": "Đơn hàng đang giao đến xxxx Huyện Mỏ Cày Nam Bến Tre",
                    "ward_code": "560909",
                    "district_id": 1975,
                    "warehouse_id": 1934,
                    "next_warehouse_id": 1934
                },
                "executor": {
                    "employee_id": 3016319,
                    "name": "xxxx Toàn",
                    "phone": "xxxx 1844"
                },
                "action_at": "2026-04-16T06:19:49.2Z",
                "sync_data_at": null
            },
            {
                "order_code": "GYKEQFDX",
                "action_code": "DELIVER_FAILED",
                "status": "delivery_fail",
                "reason": "Nhân viên gặp sự cố - Nhân viên cập nhật: Nguyễn Quốc Toàn.",
                "reason_code": "GHN-DFC1A6",
                "status_name": "Giao hàng không thành công lần 1",
                "location": {
                    "address": "Giao hàng không thành công",
                    "ward_code": "560909",
                    "district_id": 1975,
                    "warehouse_id": 1934,
                    "next_warehouse_id": 1934
                },
                "executor": {
                    "employee_id": 3016319,
                    "name": "xxxx Toàn",
                    "phone": "xxxx 1844"
                },
                "action_at": "2026-04-16T12:45:48.787Z",
                "sync_data_at": null
            },
            {
                "order_code": "GYKEQFDX",
                "action_code": "SCAN_TO_STORING",
                "status": "delivery_fail_to_storing",
                "status_name": "Nhập bưu cục giao",
                "location": {
                    "address": "Đơn hàng lưu tại Bưu Cục Mỏ Cày Nam-Bến Tre",
                    "ward_code": "560909",
                    "district_id": 1975,
                    "warehouse_id": 1934,
                    "next_warehouse_id": 1934
                },
                "executor": {
                    "employee_id": 3004516,
                    "name": "xxxx ường",
                    "phone": "xxxx 3839"
                },
                "action_at": "2026-04-16T13:09:22.918Z",
                "sync_data_at": null
            },
            {
                "order_code": "GYKEQFDX",
                "action_code": "ADD_DELIVERY_TRIP",
                "status": "storing",
                "status_name": "Sẵn sàng giao hàng",
                "location": {
                    "address": "Đơn hàng sẵn sàng được giao tại Bưu Cục Mỏ Cày Nam-Bến Tre",
                    "ward_code": "560909",
                    "district_id": 1975,
                    "warehouse_id": 1934,
                    "next_warehouse_id": 1934
                },
                "executor": {
                    "employee_id": 3004516,
                    "name": "xxxx ường",
                    "phone": "xxxx 3839"
                },
                "action_at": "2026-04-17T00:50:23.7Z",
                "sync_data_at": null
            },
            {
                "order_code": "GYKEQFDX",
                "action_code": "START_DELIVERY_TRIP",
                "status": "delivering",
                "status_name": "Đang giao hàng lần 2",
                "location": {
                    "address": "Đơn hàng đang giao đến xxxx Huyện Mỏ Cày Nam Bến Tre",
                    "ward_code": "560909",
                    "district_id": 1975,
                    "warehouse_id": 1934,
                    "next_warehouse_id": 1934
                },
                "executor": {
                    "employee_id": 3016319,
                    "name": "xxxx Toàn",
                    "phone": "xxxx 1844"
                },
                "action_at": "2026-04-17T00:50:23.753Z",
                "sync_data_at": null
            },
            {
                "order_code": "GYKEQFDX",
                "action_code": "DELIVER_FAILED",
                "status": "delivery_fail",
                "reason": "Người nhận từ chối nhận do hàng hư hỏng - Nhân viên cập nhật: Nguyễn Quốc Toàn.",
                "reason_code": "GHN-DCD0A5",
                "status_name": "Giao hàng không thành công lần 2",
                "location": {
                    "address": "Giao hàng không thành công",
                    "ward_code": "560909",
                    "district_id": 1975,
                    "warehouse_id": 1934,
                    "next_warehouse_id": 1934
                },
                "executor": {
                    "employee_id": 3016319,
                    "name": "xxxx Toàn",
                    "phone": "xxxx 1844"
                },
                "action_at": "2026-04-17T04:26:14.231Z",
                "sync_data_at": null
            },
            {
                "order_code": "GYKEQFDX",
                "action_code": "SCAN_TO_STORING",
                "status": "delivery_fail_to_storing",
                "status_name": "Nhập bưu cục giao",
                "location": {
                    "address": "Đơn hàng lưu tại Bưu Cục Mỏ Cày Nam-Bến Tre",
                    "ward_code": "560909",
                    "district_id": 1975,
                    "warehouse_id": 1934,
                    "next_warehouse_id": 1934
                },
                "executor": {
                    "employee_id": 3004516,
                    "name": "xxxx ường",
                    "phone": "xxxx 3839"
                },
                "action_at": "2026-04-17T08:03:18.756Z",
                "sync_data_at": null
            },
            {
                "order_code": "GYKEQFDX",
                "action_code": "SCAN_TO_STORING",
                "status": "waiting_to_return",
                "reason_code": "GHN-DCD0A5",
                "status_name": "Chờ xác nhận giao lại",
                "location": {
                    "address": "Đơn hàng chờ xác nhận giao lại tại Bưu Cục Mỏ Cày Nam-Bến Tre",
                    "ward_code": "560909",
                    "district_id": 1975,
                    "warehouse_id": 1934,
                    "next_warehouse_id": 1934
                },
                "executor": {
                    "employee_id": 8888
                },
                "action_at": "2026-04-17T08:03:18.777Z",
                "sync_data_at": null
            },
            {
                "order_code": "GYKEQFDX",
                "action_code": "RETURN",
                "status": "return",
                "status_name": "Chuyển hoàn",
                "location": {
                    "address": "Đơn hàng lưu tại Bưu Cục Mỏ Cày Nam-Bến Tre",
                    "ward_code": "560909",
                    "district_id": 1975,
                    "warehouse_id": 1934,
                    "next_warehouse_id": 1934
                },
                "executor": {
                    "employee_id": 8888
                },
                "action_at": "2026-04-17T08:05:10.047Z",
                "sync_data_at": null
            },
            {
                "order_code": "GYKEQFDX",
                "action_code": "PACKED_TO_SORTING",
                "status": "return",
                "status_name": "Sẵn sàng xuất đến Kho trung chuyển",
                "location": {
                    "address": "Đơn hàng chờ xuất đến Kho Trung Chuyển Dương Xá",
                    "ward_code": "560909",
                    "district_id": 1975,
                    "warehouse_id": 1934,
                    "next_warehouse_id": 21513000
                },
                "executor": {
                    "employee_id": 3004516,
                    "name": "xxxx ường",
                    "phone": "xxxx 3839"
                },
                "action_at": "2026-04-17T12:25:13.643Z",
                "sync_data_at": null
            },
            {
                "order_code": "GYKEQFDX",
                "action_code": "TRANSFER_TO_TRUCK",
                "status": "return",
                "status_name": "Xuất hàng đi khỏi kho",
                "location": {
                    "address": "Đơn hàng đã xuất khỏi Bưu Cục Mỏ Cày Nam-Bến Tre đến Kho Trung Chuyển Dương Xá",
                    "ward_code": "560909",
                    "district_id": 1975,
                    "warehouse_id": 1934,
                    "next_warehouse_id": 21513000
                },
                "executor": {
                    "employee_id": 3004516,
                    "name": "xxxx ường",
                    "phone": "xxxx 3839"
                },
                "action_at": "2026-04-17T12:28:37.108Z",
                "sync_data_at": null
            },
            {
                "order_code": "GYKEQFDX",
                "action_code": "TRANSPORTING",
                "status": "return_transporting",
                "status_name": "Đang trung chuyển hàng hoàn",
                "location": {
                    "address": "Đơn hàng đang trung chuyển đến Kho Trung Chuyển Dương Xá",
                    "ward_code": "560909",
                    "district_id": 1975,
                    "warehouse_id": 1934,
                    "next_warehouse_id": 21513000
                },
                "executor": {
                    "employee_id": 8888
                },
                "action_at": "2026-04-17T12:29:43.756Z",
                "sync_data_at": null
            },
            {
                "order_code": "GYKEQFDX",
                "action_code": "ARRIVE_AT_SORTING",
                "status": "return_transporting",
                "status_name": "Đang trung chuyển hàng hoàn",
                "location": {
                    "address": "Đơn hàng đang trung chuyển đến Kho Trung Chuyển Dương Xá",
                    "ward_code": "560909",
                    "district_id": 1975,
                    "warehouse_id": 2388,
                    "next_warehouse_id": 21513000
                },
                "executor": {
                    "employee_id": 3082179,
                    "name": "xxxx Lăng",
                    "phone": "xxxx 4181"
                },
                "action_at": "2026-04-17T14:54:19.724Z",
                "sync_data_at": null
            },
            {
                "order_code": "GYKEQFDX",
                "action_code": "RECEIVED_AT_SORTING",
                "status": "return_transporting",
                "status_name": "Nhập hàng vào kho trung chuyển",
                "location": {
                    "address": "Đơn hàng lưu tại Kho Trung Chuyển Hồ Chí Minh 20",
                    "ward_code": "560909",
                    "district_id": 1975,
                    "warehouse_id": 2388,
                    "next_warehouse_id": 21513000
                },
                "executor": {
                    "employee_id": 3082179,
                    "name": "xxxx Lăng",
                    "phone": "xxxx 4181"
                },
                "action_at": "2026-04-17T14:54:19.742Z",
                "sync_data_at": null
            },
            {
                "order_code": "GYKEQFDX",
                "action_code": "TRANSFER_TO_TRUCK",
                "status": "return_transporting",
                "status_name": "Xuất hàng đi khỏi kho",
                "location": {
                    "address": "Đơn hàng đã xuất khỏi Kho Trung Chuyển Hồ Chí Minh 20 đến Kho Trung Chuyển Dương Xá",
                    "ward_code": "560909",
                    "district_id": 1975,
                    "warehouse_id": 2388,
                    "next_warehouse_id": 21513000
                },
                "executor": {
                    "employee_id": 3138862,
                    "name": "xxxx ường",
                    "phone": "xxxx 1599"
                },
                "action_at": "2026-04-17T15:20:17.414Z",
                "sync_data_at": null
            },
            {
                "order_code": "GYKEQFDX",
                "action_code": "TRANSPORTING",
                "status": "return_transporting",
                "status_name": "Đang trung chuyển hàng hoàn",
                "location": {
                    "address": "Đơn hàng đang trung chuyển đến Kho Trung Chuyển Dương Xá",
                    "ward_code": "560909",
                    "district_id": 1975,
                    "warehouse_id": 2388,
                    "next_warehouse_id": 21513000
                },
                "executor": {
                    "employee_id": 8888
                },
                "action_at": "2026-04-17T15:21:54.738Z",
                "sync_data_at": null
            },
            {
                "order_code": "GYKEQFDX",
                "action_code": "ARRIVE_AT_SORTING",
                "status": "return_transporting",
                "status_name": "Đang trung chuyển hàng hoàn",
                "location": {
                    "address": "Đơn hàng đang trung chuyển đến Kho Trung Chuyển Dương Xá",
                    "ward_code": "560909",
                    "district_id": 1975,
                    "warehouse_id": 1121,
                    "next_warehouse_id": 21513000
                },
                "executor": {
                    "employee_id": 3155627,
                    "name": "xxxx Vênh",
                    "phone": "xxxx 3231"
                },
                "action_at": "2026-04-18T21:02:19.398Z",
                "sync_data_at": null
            },
            {
                "order_code": "GYKEQFDX",
                "action_code": "RECEIVED_AT_SORTING",
                "status": "return_transporting",
                "status_name": "Nhập hàng vào kho trung chuyển",
                "location": {
                    "address": "Đơn hàng lưu tại Kho Trung Chuyển Hà Nội 02",
                    "ward_code": "560909",
                    "district_id": 1975,
                    "warehouse_id": 1121,
                    "next_warehouse_id": 21513000
                },
                "executor": {
                    "employee_id": 3155627,
                    "name": "xxxx Vênh",
                    "phone": "xxxx 3231"
                },
                "action_at": "2026-04-18T21:02:19.415Z",
                "sync_data_at": null
            },
            {
                "order_code": "GYKEQFDX",
                "action_code": "TRANSFER_TO_TRUCK",
                "status": "return_transporting",
                "status_name": "Xuất hàng đi khỏi kho",
                "location": {
                    "address": "Đơn hàng đã xuất khỏi Kho Trung Chuyển Hà Nội 02 đến Kho Trung Chuyển Dương Xá",
                    "ward_code": "560909",
                    "district_id": 1975,
                    "warehouse_id": 1121,
                    "next_warehouse_id": 21513000
                },
                "executor": {
                    "employee_id": 3045275,
                    "name": "xxxx Thùy",
                    "phone": "xxxx 9221"
                },
                "action_at": "2026-04-18T22:40:29.981Z",
                "sync_data_at": null
            },
            {
                "order_code": "GYKEQFDX",
                "action_code": "TRANSPORTING",
                "status": "return_transporting",
                "status_name": "Đang trung chuyển hàng hoàn",
                "location": {
                    "address": "Đơn hàng đang trung chuyển đến Kho Trung Chuyển Dương Xá",
                    "ward_code": "560909",
                    "district_id": 1975,
                    "warehouse_id": 1121,
                    "next_warehouse_id": 21513000
                },
                "executor": {
                    "employee_id": 8888
                },
                "action_at": "2026-04-18T22:42:08.263Z",
                "sync_data_at": null
            },
            {
                "order_code": "GYKEQFDX",
                "action_code": "UNPACKED_AT_SORTING",
                "status": "return_transporting",
                "status_name": "Đang trung chuyển hàng hoàn",
                "location": {
                    "address": "Đơn hàng đang trung chuyển đến Kho Trung Chuyển Dương Xá",
                    "ward_code": "560909",
                    "district_id": 1975,
                    "warehouse_id": 21513000,
                    "next_warehouse_id": 21513000
                },
                "executor": {
                    "employee_id": 3143131,
                    "name": "xxxx  Anh",
                    "phone": "xxxx 8146"
                },
                "action_at": "2026-04-19T07:05:23.403Z",
                "sync_data_at": null
            },
            {
                "order_code": "GYKEQFDX",
                "action_code": "UNPACKED_AT_SORTING",
                "status": "return",
                "status_name": "Đang phân loại hàng",
                "location": {
                    "address": "Đơn hàng đang phân loại tại Kho Trung Chuyển Dương Xá",
                    "ward_code": "560909",
                    "district_id": 1975,
                    "warehouse_id": 21513000,
                    "next_warehouse_id": 21513000
                },
                "executor": {
                    "employee_id": 3143131,
                    "name": "xxxx  Anh",
                    "phone": "xxxx 8146"
                },
                "action_at": "2026-04-19T07:05:23.427Z",
                "sync_data_at": null
            },
            {
                "order_code": "GYKEQFDX",
                "action_code": "PACKED_TO_LASTMILE",
                "status": "return",
                "status_name": "Sẵn sàng xuất đến bưu cục hoàn",
                "location": {
                    "address": "Đơn hàng chờ xuất đến Bưu Cục 39 Gò Sỏi-Sóc Sơn-HN",
                    "ward_code": "560909",
                    "district_id": 1975,
                    "warehouse_id": 21513000,
                    "next_warehouse_id": 20108000
                },
                "executor": {
                    "employee_id": 3143131,
                    "name": "xxxx  Anh",
                    "phone": "xxxx 8146"
                },
                "action_at": "2026-04-19T07:05:23.501Z",
                "sync_data_at": null
            },
            {
                "order_code": "GYKEQFDX",
                "action_code": "TRANSFER_TO_TRUCK",
                "status": "return",
                "status_name": "Xuất hàng đi khỏi kho",
                "location": {
                    "address": "Đơn hàng đã xuất khỏi Kho Trung Chuyển Dương Xá đến Bưu Cục 39 Gò Sỏi-Sóc Sơn-HN",
                    "ward_code": "560909",
                    "district_id": 1975,
                    "warehouse_id": 21513000,
                    "next_warehouse_id": 20108000
                },
                "executor": {
                    "employee_id": 3143131,
                    "name": "xxxx  Anh",
                    "phone": "xxxx 8146"
                },
                "action_at": "2026-04-19T07:12:09.909Z",
                "sync_data_at": null
            },
            {
                "order_code": "GYKEQFDX",
                "action_code": "TRANSPORTING",
                "status": "return_transporting",
                "status_name": "Đang trung chuyển hàng hoàn",
                "location": {
                    "address": "Đơn hàng đang trung chuyển đến Bưu Cục 39 Gò Sỏi-Sóc Sơn-HN",
                    "ward_code": "560909",
                    "district_id": 1975,
                    "warehouse_id": 21513000,
                    "next_warehouse_id": 20108000
                },
                "executor": {
                    "employee_id": 8888
                },
                "action_at": "2026-04-19T07:13:21.936Z",
                "sync_data_at": null
            },
            {
                "order_code": "GYKEQFDX",
                "action_code": "TRANSPORTING",
                "status": "return_transporting",
                "status_name": "Đang trung chuyển hàng hoàn",
                "location": {
                    "address": "Đơn hàng đang trung chuyển đến Bưu Cục 39 Gò Sỏi-Sóc Sơn-HN",
                    "ward_code": "560909",
                    "district_id": 1975,
                    "warehouse_id": 20312000,
                    "next_warehouse_id": 20108000
                },
                "executor": {
                    "employee_id": 8888
                },
                "action_at": "2026-04-19T08:26:03.7Z",
                "sync_data_at": null
            },
            {
                "order_code": "GYKEQFDX",
                "action_code": "ARRIVE_AT_LASTMILE",
                "status": "return_transporting",
                "status_name": "Đang trung chuyển hàng hoàn",
                "location": {
                    "address": "Đơn hàng đang trung chuyển đến Bưu Cục 39 Gò Sỏi-Sóc Sơn-HN",
                    "ward_code": "560909",
                    "district_id": 1975,
                    "warehouse_id": 20108000,
                    "next_warehouse_id": 20108000
                },
                "executor": {
                    "employee_id": 3000037,
                    "name": "xxxx Châm",
                    "phone": "xxxx 5451"
                },
                "action_at": "2026-04-19T09:08:28.208Z",
                "sync_data_at": null
            },
            {
                "order_code": "GYKEQFDX",
                "action_code": "RECEIVED_AT_LASTMILE",
                "status": "return_transporting",
                "status_name": "Nhập hàng vào bưu cục hoàn",
                "location": {
                    "address": "Đơn hàng lưu tại Bưu Cục 39 Gò Sỏi-Sóc Sơn-HN",
                    "ward_code": "560909",
                    "district_id": 1975,
                    "warehouse_id": 20108000,
                    "next_warehouse_id": 20108000
                },
                "executor": {
                    "employee_id": 3000037,
                    "name": "xxxx Châm",
                    "phone": "xxxx 5451"
                },
                "action_at": "2026-04-19T09:08:28.233Z",
                "sync_data_at": null
            },
            {
                "order_code": "GYKEQFDX",
                "action_code": "UNPACKED_AT_LASTMILE",
                "status": "return_transporting",
                "status_name": "Đang trung chuyển hàng hoàn",
                "location": {
                    "address": "Đơn hàng đang trung chuyển đến Bưu Cục 39 Gò Sỏi-Sóc Sơn-HN",
                    "ward_code": "560909",
                    "district_id": 1975,
                    "warehouse_id": 20108000,
                    "next_warehouse_id": 20108000
                },
                "executor": {
                    "employee_id": 3000037,
                    "name": "xxxx Châm",
                    "phone": "xxxx 5451"
                },
                "action_at": "2026-04-19T09:08:28.281Z",
                "sync_data_at": null
            },
            {
                "order_code": "GYKEQFDX",
                "action_code": "ADD_RETURN_TRIP",
                "status": "return",
                "status_name": "Sẵn sàng hoàn hàng",
                "location": {
                    "address": "Đơn hàng lưu tại Bưu Cục 39 Gò Sỏi-Sóc Sơn-HN",
                    "ward_code": "560909",
                    "district_id": 1975,
                    "warehouse_id": 20108000,
                    "next_warehouse_id": 20108000
                },
                "executor": {
                    "employee_id": 3000037,
                    "name": "xxxx Châm",
                    "phone": "xxxx 5451"
                },
                "action_at": "2026-04-19T09:34:25.373Z",
                "sync_data_at": null
            },
            {
                "order_code": "GYKEQFDX",
                "action_code": "START_RETURN_TRIP",
                "status": "returning",
                "status_name": "Đang hoàn hàng",
                "location": {
                    "address": "Đơn hàng đang hoàn đến xxxx  Nội",
                    "ward_code": "560909",
                    "district_id": 1975,
                    "warehouse_id": 20108000,
                    "next_warehouse_id": 20108000
                },
                "executor": {
                    "employee_id": 3104655,
                    "name": "xxxx Quân",
                    "phone": "xxxx 3915"
                },
                "action_at": "2026-04-19T09:34:25.535Z",
                "sync_data_at": null
            },
            {
                "order_code": "GYKEQFDX",
                "action_code": "RETURN_IN_TRIP",
                "status": "returned",
                "status_name": "Hoàn hàng thành công",
                "location": {
                    "address": "Đơn hàng đuợc hoàn thành công tại xxxx  Nội",
                    "ward_code": "560909",
                    "district_id": 1975,
                    "warehouse_id": 20108000,
                    "next_warehouse_id": 20108000
                },
                "executor": {
                    "employee_id": 3104655,
                    "name": "xxxx Quân",
                    "phone": "xxxx 3915"
                },
                "action_at": "2026-04-19T13:36:29.083Z",
                "sync_data_at": null
            }
        ],
        "ticket_logs": [],
        "is_sender": false
    }
}