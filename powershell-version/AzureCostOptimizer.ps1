function Get-EnvVariables {
    $envFilePath = ".env"
    if (-not (Test-Path -Path $envFilePath)) {
        Write-Error "Environment variables file not found: $envFilePath"
        Stop-Transcript
        Exit 1
    }

    Get-Content -Path $envFilePath | ForEach-Object {
        if ($_ -match "^(.*?)=(.*)$") {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim('"').Trim()
            try {
                if ($name -notmatch "=") {
                    [System.Environment]::SetEnvironmentVariable($name, $value)
                } else {
                    Write-Error "Invalid environment variable name: $name"
                }
            } catch {
                Write-Error "Error setting environment variable: $name with value: $value. Exception: $_"
            }
        } else {
            Write-Warning "Ignoring invalid line in .env file: $_"
        }
    }
}

function Test-EnvVariables {
    param (
        [array]$variables
    )
    foreach ($var in $variables) {
        if (-not (Test-Path -Path "env:$var")) {
            Write-Error "${var} is not set."
            Stop-Transcript
            Exit 1
        } else {
            $envValue = (Get-Item -Path "env:${var}").Value
            Write-Output "${var}: ${envValue}"
        }
    }
}

function Import-PoliciesFromYAML {
    param (
        [string]$configFile
    )
    $configContent = Get-Content -Path $configFile -Raw
    return $configContent | ConvertFrom-Yaml
}

function Invoke-Retry {
    param (
        [scriptblock] $Command,
        [int] $MaxRetries = 3,
        [int] $Delay = 5,
        [int] $Backoff = 2
    )

    $retries = 0
    while ($retries -lt $MaxRetries) {
        try {
            return & $Command
        } catch {
            Write-Warning "Exception occurred: $_. Retrying in $Delay seconds..."
            Start-Sleep -Seconds $Delay
            $Delay *= $Backoff
            $retries++
        }
    }
    & $Command
}

function Get-ApplicationGateways {
    return Get-AzApplicationGateway
}

function Write-EmptyBackendPoolLog {
    param (
        [Parameter(Mandatory = $true)]
        [object] $Gateway,
        [switch] $DryRun
    )

    if ($DryRun) {
        Write-Output "Dry run: Logging empty backend pool for gateway: $($Gateway.Name)"
    } else {
        Write-Output "Logging empty backend pool for gateway: $($Gateway.Name)"
        # Log logic here
    }
    return @("Logged", "Empty backend pool logged")
}

function Remove-ApplicationGateway {
    param (
        [Parameter(Mandatory = $true)]
        [object] $Gateway,
        [ref] $StatusLog,
        [switch] $DryRun
    )

    if ($DryRun) {
        Write-Output "Dry run: Deleting Application Gateway: $($Gateway.Name)"
        return @("Dry Run", "Dry run: Gateway deletion simulated")
    } else {
        Remove-AzApplicationGateway -Name $Gateway.Name -ResourceGroupName $Gateway.ResourceGroupName -Force
        Write-Output "Deleted Application Gateway: $($Gateway.Name)"
        return @("Deleted", "Application Gateway deleted")
    }
}

function Invoke-AppGatewayActions {
    param (
        [Parameter(Mandatory = $true)]
        [object] $Gateway,
        [Parameter(Mandatory = $true)]
        [array] $Actions,
        [ref] $StatusLog,
        [switch] $DryRun
    )

    $status = "No Change"
    $message = "No applicable actions found"

    foreach ($action in $Actions) {
        $actionType = $action.type
        if ($actionType -eq "log") {
            $result = Write-EmptyBackendPoolLog -Gateway $Gateway -DryRun:$DryRun
            $status = $result[0]
            $message = $result[1]
        } elseif ($actionType -eq "delete") {
            try {
                $result = Remove-ApplicationGateway -Gateway $Gateway -StatusLog ([ref] $StatusLog) -DryRun:$DryRun
                $status = $result[0]
                $message = $result[1]
            } catch {
                Write-Error "Failed to delete application gateway: $_"
            }
        }
    }

    return @($status, $message)
}

function Test-VMStopped {
    param (
        [Parameter(Mandatory = $true)]
        [object] $VM
    )

    $resourceGroupName = $VM.ResourceGroupName
    $instanceView = Get-AzVM -ResourceGroupName $resourceGroupName -Name $VM.Name -Status
    $statuses = $instanceView.Statuses
    return $statuses | Where-Object { $_.Code -eq 'PowerState/deallocated' }
}

function Stop-AzureVM {
    param (
        [Parameter(Mandatory = $true)]
        [object] $VM,
        [switch] $DryRun
    )

    if ($DryRun) {
        Write-Output "Dry run: Stopping VM: $($VM.Name)"
        return @("Dry Run", "Dry run: VM stop simulated")
    } else {
        Stop-AzVM -ResourceGroupName $VM.ResourceGroupName -Name $VM.Name -Force
        Write-Output "Stopped VM: $($VM.Name)"
        return @("Stopped", "VM stopped successfully")
    }
}

function Test-DiskUnattached {
    param (
        [Parameter(Mandatory = $true)]
        [object] $Disk
    )

    return -not $Disk.ManagedBy
}

function Remove-Disk {
    param (
        [Parameter(Mandatory = $true)]
        [object] $Disk,
        [switch] $DryRun
    )

    if ($DryRun) {
        Write-Output "Dry run: Deleting Disk: $($Disk.Name)"
        return @("Dry Run", "Dry run: Disk deletion simulated")
    } else {
        Remove-AzDisk -ResourceGroupName $Disk.ResourceGroupName -DiskName $Disk.Name -Force
        Write-Output "Deleted Disk: $($Disk.Name)"
        return @("Deleted", "Disk deleted successfully")
    }
}

function Test-NICUnattached {
    param (
        [Parameter(Mandatory = $true)]
        [object] $NIC
    )

    return -not $NIC.VirtualMachine
}

function Remove-NIC {
    param (
        [Parameter(Mandatory = $true)]
        [object] $NIC,
        [switch] $DryRun
    )

    if ($DryRun) {
        Write-Output "Dry run: Deleting NIC: $($NIC.Name)"
        return @("Dry Run", "Dry run: NIC deletion simulated")
    } else {
        Remove-AzNetworkInterface -ResourceGroupName $NIC.ResourceGroupName -Name $NIC.Name -Force
        Write-Output "Deleted NIC: $($NIC.Name)"
        return @("Deleted", "NIC deleted successfully")
    }
}

function Test-PIPUnattached {
    param (
        [Parameter(Mandatory = $true)]
        [object] $PIP
    )

    return -not $PIP.IpConfiguration
}

function Remove-PIP {
    param (
        [Parameter(Mandatory = $true)]
        [object] $PIP,
        [switch] $DryRun
    )

    if ($DryRun) {
        Write-Output "Dry run: Deleting Public IP: $($PIP.Name)"
        return @("Dry Run", "Dry run: Public IP deletion simulated")
    } else {
        Remove-AzPublicIpAddress -ResourceGroupName $PIP.ResourceGroupName -Name $PIP.Name -Force
        Write-Output "Deleted Public IP: $($PIP.Name)"
        return @("Deleted", "Public IP deleted successfully")
    }
}

function Set-SQLDatabaseScale {
    param (
        [Parameter(Mandatory = $true)]
        [object] $Database,
        [Parameter(Mandatory = $true)]
        [string] $NewDTU,
        [Parameter(Mandatory = $true)]
        [string] $MinDTU,
        [Parameter(Mandatory = $true)]
        [string] $MaxDTU,
        [switch] $DryRun
    )

    if ($DryRun) {
        Write-Output "Dry run: Scaling SQL Database: $($Database.Name) to DTU: $NewDTU"
        return @("Dry Run", "Dry run: SQL Database scaling simulated")
    } else {
        $currentSku = $Database.Sku
        $resourceGroupName = $Database.ResourceGroupName
        $serverName = $Database.ServerName

        $newSku = @{
            "Name"     = $currentSku.Name
            "Tier"     = $currentSku.Tier
            "Capacity" = $NewDTU
        }

        Set-AzSqlDatabase -ResourceGroupName $resourceGroupName -ServerName $serverName -DatabaseName $Database.Name -Edition $currentSku.Tier -RequestedServiceObjectiveName $newSku.Name -ComputeModel $newSku.Capacity

        Write-Output "Scaled SQL Database: $($Database.Name) to DTU: $NewDTU"
        return @("Scaled", "SQL Database scaled successfully")
    }
}

function Set-StorageAccountSKU {
    param (
        [Parameter(Mandatory = $true)]
        [object] $StorageAccount,
        [Parameter(Mandatory = $true)]
        [string] $NewSKU,
        [switch] $DryRun
    )

    if ($DryRun) {
        Write-Output "Dry run: Updating Storage Account SKU: $($StorageAccount.Name) to SKU: $NewSKU"
        return @("Dry Run", "Dry run: Storage Account SKU update simulated")
    } else {
        Set-AzStorageAccount -ResourceGroupName $StorageAccount.ResourceGroupName -Name $StorageAccount.Name -SkuName $NewSKU
        Write-Output "Updated Storage Account SKU: $($StorageAccount.Name) to SKU: $NewSKU"
        return @("Updated", "Storage Account SKU updated successfully")
    }
}

function Test-Filters {
    param (
        [Parameter(Mandatory = $true)]
        [object] $Resource,
        [Parameter(Mandatory = $true)]
        [array] $Filters
    )

    foreach ($filter in $Filters) {
        $filterType = $filter.type
        if ($filterType -eq "last_used") {
            $days = $filter.days
            $threshold = $filter.threshold
            if (-not (Test-LastUsedFilter -Resource $Resource -Days $days -Threshold $threshold)) {
                return $false
            }
        } elseif ($filterType -eq "unattached") {
            if (-not (Test-UnattachedFilter -Resource $Resource)) {
                return $false
            }
        } elseif ($filterType -eq "tag") {
            $key = $filter.key
            $value = $filter.value
            if (-not (Test-TagFilter -Resource $Resource -Key $key -Value $value)) {
                return $false
            }
        } elseif ($filterType -eq "sku") {
            $values = $filter.values
            if (-not (Test-SKUFilter -Resource $Resource -Values $values)) {
                return $false
            }
        } elseif ($filterType -eq "stopped") {
            if (-not (Test-VMStopped -VM $Resource)) {
                return $false
            }
        }
    }
    return $true
}

function Invoke-Actions {
    param (
        [Parameter(Mandatory = $true)]
        [object] $Resource,
        [Parameter(Mandatory = $true)]
        [array] $Actions,
        [ref] $StatusLog,
        [switch] $DryRun
    )

    foreach ($action in $Actions) {
        $actionType = $action.type
        if ($actionType -eq "stop") {
            $result = Stop-AzureVM -VM $Resource -DryRun:$DryRun
        } elseif ($actionType -eq "delete") {
            if ($Resource.GetType().Name -eq "Disk") {
                $result = Remove-Disk -Disk $Resource -DryRun:$DryRun
            } elseif ($Resource.GetType().Name -eq "NetworkInterface") {
                $result = Remove-NIC -NIC $Resource -DryRun:$DryRun
            } elseif ($Resource.GetType().Name -eq "PublicIpAddress") {
                $result = Remove-PIP -PIP $Resource -DryRun:$DryRun
            }
        } elseif ($actionType -eq "scale_dtu") {
            $result = Set-SQLDatabaseScale -Database $Resource -NewDTU $action.NewDTU -MinDTU $action.MinDTU -MaxDTU $action.MaxDTU -DryRun:$DryRun
        } elseif ($actionType -eq "update_sku") {
            $result = Set-StorageAccountSKU -StorageAccount $Resource -NewSKU $action.SKU -DryRun:$DryRun
        }
        $statusLog.Value += @{
            SubscriptionId = $Resource.SubscriptionId
            Resource       = $Resource.Name
            Action         = $actionType
            Status         = $result[0]
            Message        = $result[1]
        }
    }
}

function Invoke-Resources {
    param (
        [Parameter(Mandatory = $true)]
        [array] $Policies,
        [Parameter(Mandatory = $true)]
        [string] $Mode,
        [ref] $StatusLog
    )

    foreach ($policy in $Policies) {
        $resourceType = $policy.resource
        $filters = $policy.filters
        $actions = $policy.actions

        if ($resourceType -eq "azure.vm") {
            $vms = Get-AzVM
            foreach ($vm in $vms) {
                if (Test-Filters -Resource $vm -Filters $filters) {
                    Invoke-Actions -Resource $vm -Actions $actions -StatusLog ([ref] $StatusLog) -DryRun:($Mode -eq "dry-run")
                }
            }
        } elseif ($resourceType -eq "azure.disk") {
            $disks = Get-AzDisk
            foreach ($disk in $disks) {
                if (Test-Filters -Resource $disk -Filters $filters) {
                    Invoke-Actions -Resource $disk -Actions $actions -StatusLog ([ref] $StatusLog) -DryRun:($Mode -eq "dry-run")
                }
            }
        } elseif ($resourceType -eq "azure.nic") {
            $nics = Get-AzNetworkInterface
            foreach ($nic in $nics) {
                if (Test-Filters -Resource $nic -Filters $filters) {
                    Invoke-Actions -Resource $nic -Actions $actions -StatusLog ([ref] $StatusLog) -DryRun:($Mode -eq "dry-run")
                }
            }
        } elseif ($resourceType -eq "azure.publicip") {
            $pips = Get-AzPublicIpAddress
            foreach ($pip in $pips) {
                if (Test-Filters -Resource $pip -Filters $filters) {
                    Invoke-Actions -Resource $pip -Actions $actions -StatusLog ([ref] $StatusLog) -DryRun:($Mode -eq "dry-run")
                }
            }
        } elseif ($resourceType -eq "azure.sql") {
            $servers = Get-AzSqlServer
            foreach ($server in $servers) {
                $databases = Get-AzSqlDatabase -ResourceGroupName $server.ResourceGroupName -ServerName $server.ServerName
                foreach ($database in $databases) {
                    if (Test-Filters -Resource $database -Filters $filters) {
                        Invoke-Actions -Resource $database -Actions $actions -StatusLog ([ref] $StatusLog) -DryRun:($Mode -eq "dry-run")
                    }
                }
            }
        } elseif ($resourceType -eq "azure.storage") {
            $storageAccounts = Get-AzStorageAccount
            foreach ($storageAccount in $storageAccounts) {
                if (Test-Filters -Resource $storageAccount -Filters $filters) {
                    Invoke-Actions -Resource $storageAccount -Actions $actions -StatusLog ([ref] $StatusLog) -DryRun:($Mode -eq "dry-run")
                }
            }
        } elseif ($resourceType -eq "azure.applicationgateway") {
            $gateways = Get-ApplicationGateways
            foreach ($gateway in $gateways) {
                if (Test-Filters -Resource $gateway -Filters $filters) {
                    Invoke-AppGatewayActions -Gateway $gateway -Actions $actions -StatusLog ([ref] $StatusLog) -DryRun:($Mode -eq "dry-run")
                }
            }
        }
    }
}

function Invoke-AzureCostOptimizer {
    param (
        [Parameter(Mandatory = $true)]
        [ValidateSet("dry-run", "apply")]
        [string]$Mode
    )

    # Ensure required modules are installed
    $requiredModules = @("Az", "Az.CostManagement", "Az.Compute", "Az.Storage", "Az.Network", "Az.Sql", "Az.Monitor", "Az.Accounts", "powershell-yaml")
    foreach ($module in $requiredModules) {
        if (-not (Get-Module -ListAvailable -Name $module)) {
            Install-Module -Name $module -Force -Scope CurrentUser
        }
    }

    # Import required modules
    Import-Module -Name Az
    Import-Module -Name Az.CostManagement
    Import-Module -Name Az.Compute
    Import-Module -Name Az.Storage
    Import-Module -Name Az.Network
    Import-Module -Name Az.Sql
    Import-Module -Name Az.Monitor
    Import-Module -Name Az.Accounts
    Import-Module -Name powershell-yaml

    # Authenticate to Azure
    Connect-AzAccount

    # Authenticate to Azure
    Connect-AzAccount

    # Load environment variables
    Get-EnvVariables

    # Verify required environment variables are set
    $requiredEnvVars = @(
        "AZURE_CLIENT_ID", "AZURE_TENANT_ID", "AZURE_CLIENT_SECRET",
        "AZURE_SUBSCRIPTION_ID", "AZURE_STORAGE_ACCOUNT_NAME",
        "AZURE_STORAGE_FILE_SYSTEM_NAME", "ADLS_DIRECTORY_PATH"
    )
    Test-EnvVariables -variables $requiredEnvVars

    # Load policies from YAML configuration
    $configFile = "configs/config.yaml"
    $config = Import-PoliciesFromYAML -configFile $configFile

    $statusLog = @()
    Invoke-Resources -Policies $config.policies -Mode $Mode -StatusLog ([ref]$statusLog)

    # Log status to Application Insights (or other logging mechanisms)
    foreach ($logEntry in $statusLog) {
        Write-Output ("${logEntry.Resource}: ${logEntry.Action} - ${logEntry.Status}: ${logEntry.Message}")

        # Example to send telemetry data (customize as per your telemetry setup)
        # $tc.TrackEvent("AzureCostOptimization", @{
        #     "SubscriptionId" = $logEntry.SubscriptionId
        #     "Resource"       = $logEntry.Resource
        #     "Action"         = $logEntry.Action
        #     "Status"         = $logEntry.Status
        #     "Message"        = $logEntry.Message
        # })
    }
    # $tc.Flush()

}

# Example usage: Run in dry-run mode
Invoke-AzureCostOptimizer -Mode "dry-run"
