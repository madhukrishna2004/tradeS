document.addEventListener("DOMContentLoaded", () => {
    // Dark Mode Toggle
    document.getElementById("toggleMode").addEventListener("click", () => {
        const body = document.body;
        body.classList.toggle("dark");
        body.classList.toggle("light");
        document.getElementById("toggleMode").innerText = body.classList.contains("dark") ? "☀️ Light Mode" : "🌙 Dark Mode";
    });

    // Step 1: Generate Auth URL
    document.getElementById("generateAuthUrl").addEventListener("click", async () => {
        const client_id = document.getElementById("client_id").value;

        if (!client_id) {
            alert("Please enter Client ID!");
            return;
        }

        try {
            const response = await fetch("/generate_auth_url", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ client_id })
            });

            const data = await response.json();
            if (data.auth_url) {
                document.getElementById("authUrlContainer").innerHTML = `
                    <p class="text-green-500">Click below to authenticate:</p>
                    <a href="${data.auth_url}" target="_blank" class="text-blue-500 underline">Authenticate Here</a>
                `;
            } else {
                document.getElementById("authUrlContainer").innerHTML = `<p class="text-red-500">Error generating URL.</p>`;
            }
        } catch (error) {
            console.error("Error:", error);
            document.getElementById("authUrlContainer").innerHTML = `<p class="text-red-500">Error generating URL.</p>`;
        }
    });

    // Step 3: Exchange Auth Code for Access Token
    document.getElementById("exchangeToken").addEventListener("click", async () => {
        const client_id = document.getElementById("client_id").value;
        const auth_code = document.getElementById("auth_code").value;

        if (!client_id || !auth_code) {
            alert("Please enter Client ID and Authorization Code!");
            return;
        }

        try {
            const response = await fetch("/exchange_token", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ client_id, auth_code })
            });

            const data = await response.json();
            if (data.access_token) {
                document.getElementById("access_token").value = data.access_token;
                alert("Access Token Generated Successfully!");
            } else {
                alert("Failed to get Access Token.");
            }
        } catch (error) {
            console.error("Error:", error);
            alert("Error exchanging token.");
        }
    });

    // Step 4: Run Strategy
    document.getElementById("runStrategy").addEventListener("click", async () => {
        const client_id = document.getElementById("client_id").value;
        const access_token = document.getElementById("access_token").value;

        if (!client_id || !access_token) {
            alert("Please enter Client ID and Access Token!");
            return;
        }

        document.getElementById("loading").classList.remove("hidden");
        document.getElementById("result").innerHTML = "";

        try {
            const response = await fetch("/run_strategy", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ client_id, access_token })
            });

            const data = await response.json();
            document.getElementById("loading").classList.add("hidden");

            let resultHTML = `<h2 class="text-lg font-bold">📊 Strategy Results</h2>`;

            if (Object.keys(data).length === 0) {
                resultHTML += `<p class="text-red-500">No data found.</p>`;
            } else {
                resultHTML += `<div class="overflow-x-auto mt-4">
                    <table class="w-full border-collapse border border-gray-300 dark:border-gray-700">
                        <thead class="bg-gray-200 dark:bg-gray-800">
                            <tr>
                                <th class="border border-gray-300 dark:border-gray-700 px-4 py-2">Symbol</th>
                                <th class="border border-gray-300 dark:border-gray-700 px-4 py-2">20D High</th>
                                <th class="border border-gray-300 dark:border-gray-700 px-4 py-2">Yesterday Close</th>
                                <th class="border border-gray-300 dark:border-gray-700 px-4 py-2">LTP</th>
                                <th class="border border-gray-300 dark:border-gray-700 px-4 py-2">% Diff (Y.Close)</th>
                                <th class="border border-gray-300 dark:border-gray-700 px-4 py-2">% Diff (20D High)</th>
                                <th class="border border-gray-300 dark:border-gray-700 px-4 py-2">Signal</th>
                                <th class="border border-gray-300 dark:border-gray-700 px-4 py-2">Target Price</th>
                                <th class="border border-gray-300 dark:border-gray-700 px-4 py-2">Stop Loss</th>
                                <th class="border border-gray-300 dark:border-gray-700 px-4 py-2">Trailing SL</th>
                            </tr>
                        </thead>
                        <tbody class="text-center">`;

                Object.keys(data).forEach(symbol => {
                    let stockData = data[symbol];
                    if (typeof stockData === "object") {
                        let color = stockData["Signal"] === "✅ Buy" ? "text-green-500" : "text-red-500";
                        resultHTML += `<tr class="border border-gray-300 dark:border-gray-700">
                            <td class="px-4 py-2 border">${symbol}</td>
                            <td class="px-4 py-2 border">${stockData["20D High"]}</td>
                            <td class="px-4 py-2 border">${stockData["Yesterday Close"]}</td>
                            <td class="px-4 py-2 border">${stockData["LTP"]}</td>
                            <td class="px-4 py-2 border">${stockData["% Diff (Y.Close)"]}</td>
                            <td class="px-4 py-2 border">${stockData["% Diff (20D High)"]}</td>
                            <td class="px-4 py-2 border font-bold ${color}">${stockData["Signal"]}</td>
                            <td class="px-4 py-2 border">${stockData["Target Price"]}</td>
                            <td class="px-4 py-2 border">${stockData["Stop Loss"]}</td>
                            <td class="px-4 py-2 border">${stockData["Trailing SL"]}</td>
                        </tr>`;
                    } else {
                        resultHTML += `<tr><td colspan="10" class="text-red-500 px-4 py-2">${symbol}: ${stockData}</td></tr>`;
                    }
                });

                resultHTML += `</tbody></table></div>`;
            }

            document.getElementById("result").innerHTML = resultHTML;
        } catch (error) {
            document.getElementById("loading").classList.add("hidden");
            document.getElementById("result").innerHTML = `<p class="text-red-500">Error fetching data.</p>`;
            console.error("Error:", error);
        }
    });
});
