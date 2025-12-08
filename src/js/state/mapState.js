import { observable, action, reaction } from 'mobx'
import L from 'leaflet'

import { Lmock, Lfootprint, Lmyposition } from 'component/LMapMarker'
import authConstnat from 'constant/auth'
import mapConstant from 'constant/map'
import api from 'api';

// Simple debounce utility
const debounce = (fn, delay) => {
    let timeoutId;
    return (...args) => {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => fn(...args), delay);
    };
};


class Map {
    map
    mockGroup
    mypositionGroup
    footprintGroup
    liveFootprintGroup
    isInitialized = false  // Flag to prevent API calls before geolocation
    @observable mockposition = null  // Start as null, set when geolocation resolves


    init = (map) => {
        this.map = map
        // Set default Style
        // L.gridLayer.googleMutant({
        //     type:'roadmap'  // valid values are 'roadmap', 'satellite', 'terrain' and 'hybrid'
        // }).addTo(this.map)

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(this.map);

        this.map.removeControl(this.map.zoomControl)


        // init layerGroup
        this.mockGroup = L.layerGroup().addTo(this.map)
        this.mypositionGroup = L.layerGroup().addTo(this.map)
        this.footprintGroup = L.layerGroup().addTo(this.map)
        this.liveFootprintGroup = L.layerGroup().addTo(this.map)

        // Debounced moveend handler to prevent excessive API calls during panning
        // Only triggers AFTER isInitialized is true (after first setMyPosition)
        const debouncedMoveEnd = debounce(() => {
            if (!this.isInitialized) {
                console.log('DEBUG: Map moveend ignored - waiting for geolocation')
                return
            }
            const center = this.map.getCenter()
            console.log('DEBUG: Map moveend (debounced). Updating mockposition to:', center)
            this.mockTo(center)
        }, 300)

        this.map.on('moveend', debouncedMoveEnd)
    }

    @action mockTo = (position) => {
        console.log('DEBUG: mapState.mockTo called with:', position)
        this.mockposition = position
        this.mockGroup.clearLayers()

        L.marker(position, { icon: Lmock, zIndexOffset: 1000 })
            .addTo(this.mockGroup)
        this.mockGroup.addTo(this.map)
    }

    @action setMyPosition = (position, zoomsize) => {
        this.map.setView(position, zoomsize)
        this.mockTo(position)

        this.mypositionGroup.clearLayers()
        L.marker(position, { icon: Lmyposition, zIndexOffset: 10 })
            .addTo(this.mypositionGroup)
        this.mypositionGroup.addTo(this.map)

        // Enable moveend listener after first position is set
        this.isInitialized = true
        console.log('DEBUG: Map initialized with position:', position)
    }

    setFootprintbyRequest = (id) => {
        this.footprintGroup.clearLayers() // Clear history only
        api.footprintRequest({
            id: id,
            CSRF_TOKEN: authConstnat.CSRF_TOKEN
        })
            .then(footprints => {
                if (footprints.length) {
                    let latest = footprints.slice(-1)[0]
                    this.map.setView(latest, mapConstant.DistrictZoomSize)

                    footprints.map((position) => {
                        L.marker(position, { icon: Lfootprint, zIndexOffset: 2000 }).addTo(this.footprintGroup)
                    })
                    this.footprintGroup.addTo(this.map)
                }
            })
    }

    setFootprint(position) {
        console.log('DEBUG: setFootprint called with:', position)
        this.liveFootprintGroup.clearLayers() // Clear previous live marker
        this.map.setView(position, mapConstant.StreetZoomSize)
        const marker = L.marker(position, { icon: Lfootprint })
        marker.addTo(this.liveFootprintGroup)
        this.liveFootprintGroup.addTo(this.map)
        console.log('DEBUG: liveFootprintGroup has layers:', this.liveFootprintGroup.getLayers().length)
    }


    clearFootprint = () => {
        this.footprintGroup.clearLayers()
        this.liveFootprintGroup.clearLayers()
        this.footprintGroup.addTo(this.map)
        this.liveFootprintGroup.addTo(this.map)
    }


    registClickMock = () => {
        this.map.addEventListener('click', this.onMapClick)
    }

    unregistClickMock = () => {
        this.map.removeEventListener('click', this.onMapClick)
    }


    onMapClick = (e) => {
        const position = e.latlng
        this.mockTo(position)
    }



}

export default new Map()

