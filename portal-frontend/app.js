"use strict";

const form = document.getElementById("create-instance-form");
const instanceNameInput = document.getElementById("instance-name");
const createButton = document.getElementById("create-button");

const resultPanel = document.getElementById("result-panel");
const resultOutput = document.getElementById("result-output");
const statusBadge = document.getElementById("status-badge");

const config = window.PLATFORM_CONFIG;

function setStatus(status, text) {
    statusBadge.textContent = text;

    statusBadge.className = "status-badge";

    if (status === "pending") {
        statusBadge.classList.add("status-pending");
    } else if (status === "success") {
        statusBadge.classList.add("status-success");
    } else if (status === "error") {
        statusBadge.classList.add("status-error");
    }
}

function showResult(payload) {
    resultPanel.classList.remove("hidden");
    resultOutput.textContent = JSON.stringify(payload, null, 2);
}

function validateInstanceName(instanceName) {
    const allowedPattern = /^[a-z0-9-]{3,30}$/;

    if (!allowedPattern.test(instanceName)) {
        throw new Error(
            "Instance name must contain 3–30 lowercase letters, numbers, or hyphens."
        );
    }

    if (instanceName.startsWith("-") || instanceName.endsWith("-")) {
        throw new Error(
            "Instance name cannot start or end with a hyphen."
        );
    }
}

function createMockResponse(instanceName) {
    return {
        requestId: crypto.randomUUID(),
        status: "SUCCEEDED",
        product: "basic-ec2",
        instanceName,
        region: "eu-west-1",
        message: "Mock mode: no AWS resources were created."
    };
}

async function sendProvisioningRequest(instanceName) {
    if (config.MOCK_MODE) {
        await new Promise((resolve) => setTimeout(resolve, 900));

        return createMockResponse(instanceName);
    }

    if (!config.API_GATEWAY_URL) {
        throw new Error(
            "API_GATEWAY_URL is empty. Configure it in config.js."
        );
    }

    const endpoint =
        `${config.API_GATEWAY_URL}${config.CREATE_INSTANCE_PATH}`;

    const response = await fetch(endpoint, {
        method: "POST",

        headers: {
            "Content-Type": "application/json"
        },

        body: JSON.stringify({
            instanceName
        })
    });

    let responseBody;

    try {
        responseBody = await response.json();
    } catch {
        responseBody = {
            message: "The API returned a non-JSON response."
        };
    }

    if (!response.ok) {
        const apiMessage =
            responseBody.message ||
            `Provisioning failed with HTTP ${response.status}.`;

        throw new Error(apiMessage);
    }

    return responseBody;
}

form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const instanceName = instanceNameInput.value.trim();

    resultPanel.classList.remove("hidden");
    createButton.disabled = true;
    createButton.textContent = "Submitting request...";

    setStatus("pending", "In progress");

    showResult({
        status: "IN_PROGRESS",
        product: "basic-ec2",
        instanceName
    });

    try {
        validateInstanceName(instanceName);

        const result = await sendProvisioningRequest(instanceName);

        setStatus("success", "Succeeded");
        showResult(result);
    } catch (error) {
        console.error(error);

        setStatus("error", "Failed");

        showResult({
            status: "FAILED",
            message:
                error instanceof Error
                    ? error.message
                    : "An unexpected error occurred."
        });
    } finally {
        createButton.disabled = false;
        createButton.textContent = "Create EC2 Instance";
    }
});