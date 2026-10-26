# AWS Self-Service Platform - retrieve public IP and application health URL.
# Run from any directory after configuring AWS CLI credentials.
param(
    [string]$StackName = 'self-service-asg-test01',
    [string]$Region = 'eu-north-1'
)

$ErrorActionPreference = 'Stop'

try {
    # External IP as observed by an AWS-hosted endpoint.
    $PublicIp = (Invoke-RestMethod -Uri 'https://checkip.amazonaws.com' -TimeoutSec 15).Trim()
    $ParsedIp = $null
    if (-not [System.Net.IPAddress]::TryParse($PublicIp, [ref]$ParsedIp) -or
        $ParsedIp.AddressFamily -ne [System.Net.Sockets.AddressFamily]::InterNetwork) {
        throw "AWS checkip returned an invalid public IPv4 address: $PublicIp"
    }
    $AllowedCidr = "$PublicIp/32"

    # Fetch the ALB DNS name from the CloudFormation stack output.
    $AlbDns = (& aws cloudformation describe-stacks `
        --stack-name $StackName `
        --region $Region `
        --query "Stacks[0].Outputs[?OutputKey=='LoadBalancerDNS'].OutputValue | [0]" `
        --output text 2>&1)
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to read CloudFormation stack '$StackName': $($AlbDns -join ' ')"
    }
    $AlbDns = ($AlbDns | Out-String).Trim()
    if ([string]::IsNullOrWhiteSpace($AlbDns) -or $AlbDns -eq 'None') {
        throw "Stack '$StackName' has no LoadBalancerDNS output."
    }

    $HealthUrl = "http://$AlbDns/health"
    Set-Clipboard -Value $HealthUrl

    Write-Host "Public IPv4 : $PublicIp"
    Write-Host "Allowed CIDR: $AllowedCidr"
    Write-Host "ALB DNS     : $AlbDns"
    Write-Host "Health URL  : $HealthUrl"
    Write-Host 'Health URL copied to clipboard.' -ForegroundColor Green
    Write-Host 'Note: Public IP is for AllowedCidr; it is not part of the health URL.'
}
catch {
    Write-Error $_.Exception.Message
    exit 1
}
