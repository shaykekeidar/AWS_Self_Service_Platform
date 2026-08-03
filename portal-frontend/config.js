"use strict";

/*
 * MOCK_MODE:
 * true  = do not call AWS; simulate a successful response.
 * false = send the request to API_GATEWAY_URL.
 */
window.PLATFORM_CONFIG = {
    MOCK_MODE: true,

    /*
     * Replace this later with the API Gateway endpoint.
     *
     * Example:
     * https://abc123.execute-api.eu-west-1.amazonaws.com
     */
    API_GATEWAY_URL: "",

    CREATE_INSTANCE_PATH: "/products/basic-ec2"
};