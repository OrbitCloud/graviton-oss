from enum import Enum


class AppSignInAudience(str, Enum):
    AzureADMyOrg = "AzureADMyOrg"
    AzureADMultipleOrgs = "AzureADMultipleOrgs"
    AzureADandPersonalMicrosoftAccount = "AzureADandPersonalMicrosoftAccount"
    PersonalMicrosoftAccount = "PersonalMicrosoftAccount"
